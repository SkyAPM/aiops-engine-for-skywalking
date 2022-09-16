# SPDX-License-Identifier: MIT

import base64
import logging
import re
import time
import zlib
from typing import Optional, List, NamedTuple

import jsonpickle
from cachetools import LRUCache, cachedmethod, Cache

from drain_parser.drain import Drain, LogCluster
from drain_parser.masking import LogMasker
from drain_parser.persistence_handler import PersistenceHandler
from drain_parser.simple_profiler import Profiler, NullProfiler, SimpleProfiler
from drain_parser.template_miner_config import TemplateMinerConfig

logger = logging.getLogger(__name__)

config_filename = 'drain3.ini'

ExtractedParameter = NamedTuple('ExtractedParameter', [('value', str), ('mask_name', str)])

# A new part is added to store logs and corresponding clusters
class LogCache(LRUCache):
    def __missing__(self, key):
        return None
    def get(self, key):
        """
        Returns the value of the item with the specified key without updating
        the cache eviction algorithm.
        """
        return Cache.__getitem__(self, key)


class TemplateMiner:

    def __init__(self,
                 persistence_handler: PersistenceHandler = None,
                 config: TemplateMinerConfig = None, config_filename=None):
        """
        Wrapper for Drain with persistence and masking support

        :param persistence_handler: The type of persistence to use. When None, no persistence is applied.
        :param config: Configuration object. When none, configuration is loaded from default .ini file (if exist)
        """
        # logger.info('Starting Drain3 template miner')

        if config is None:
            logger.info(f'Loading configuration from {config_filename}')
            config = TemplateMinerConfig()
            config.load(config_filename)

        self.config = config

        self.profiler: Profiler = NullProfiler()
        if self.config.profiling_enabled:
            self.profiler = SimpleProfiler()

        self.persistence_handler = persistence_handler

        param_str = self.config.mask_prefix + '*' + self.config.mask_suffix
        self.drain = Drain(
            sim_th=self.config.drain_sim_th,
            depth=self.config.drain_depth,
            max_children=self.config.drain_max_children,
            max_clusters=self.config.drain_max_clusters,
            max_logs=self.config.drain_max_logs,
            extra_delimiters=self.config.drain_extra_delimiters,
            profiler=self.profiler,
            param_str=param_str,
            parametrize_numeric_tokens=self.config.parametrize_numeric_tokens
        )
        self.masker = LogMasker(self.config.masking_instructions, self.config.mask_prefix, self.config.mask_suffix)
        self.parameter_extraction_cache = LRUCache(self.config.parameter_extraction_cache_capacity)
        self.last_save_time = time.time()
        if persistence_handler is not None:
            self.load_state()

        self.log_cache = LogCache(self.drain.max_logs)
        self.log_cluster_cache = LogCache(self.drain.max_logs)
        self.id_to_log = 0

    def load_state(self):
        logger.info('Checking for saved state')

        state = self.persistence_handler.load_state()
        if state is None:
            logger.info('Saved state not found')
            return

        if self.config.snapshot_compress_state:
            state = zlib.decompress(base64.b64decode(state))

        loaded_drain: Drain = jsonpickle.loads(state, keys=True)

        # json-pickle encoded keys as string by default, so we have to convert those back to int
        # this is only relevant for backwards compatibility when loading a snapshot of drain <= v0.9.1
        # which did not use json-pickle's keys=true
        if len(loaded_drain.id_to_cluster) > 0 and isinstance(next(iter(loaded_drain.id_to_cluster.keys())), str):
            loaded_drain.id_to_cluster = {int(k): v for k, v in list(loaded_drain.id_to_cluster.items())}
            if self.config.drain_max_clusters:
                cache = LRUCache(maxsize=self.config.drain_max_clusters)
                cache.update(loaded_drain.id_to_cluster)
                loaded_drain.id_to_cluster = cache

        self.drain.id_to_cluster = loaded_drain.id_to_cluster
        self.drain.clusters_counter = loaded_drain.clusters_counter
        self.drain.root_nodes = loaded_drain.root_nodes

        logger.info(f'Restored {len(loaded_drain.clusters)} clusters built from {loaded_drain.get_total_cluster_size()} messages')

    def save_state(self, snapshot_reason):
        state = jsonpickle.dumps(self.drain, keys=True).encode('utf-8')
        if self.config.snapshot_compress_state:
            state = base64.b64encode(zlib.compress(state))

        logger.info(f'Saving state of {len(self.drain.clusters)} clusters '
                    f'with {self.drain.get_total_cluster_size()} messages, {len(state)} bytes, '
                    f'reason: {snapshot_reason}')
        self.persistence_handler.save_state(state)

    def get_snapshot_reason(self, change_type, cluster_id):
        if change_type != 'none':
            return f'{change_type} ({cluster_id})'

        diff_time_sec = time.time() - self.last_save_time
        if diff_time_sec >= self.config.snapshot_interval_minutes * 60:
            return 'periodic'

        return None


    def get_cluster(self, mask_content: str, log_service: str) -> dict:
        """
        Perform clustering according to mask content, and get the clustering result
        @param mask_content:
        @param log_service: the service name of the log
        @return:the result of the attribute containing the cluster
        """
        mask_id = self.log_cache.get(mask_content)
        if mask_id is None:
            self.id_to_log += 1
            self.log_cache[mask_content] = self.id_to_log

            self.profiler.start_section('drain')

            cluster, change_type = self.drain.add_log_message(mask_content, log_service)
            self.log_cluster_cache[self.id_to_log] = cluster
            self.profiler.end_section('drain')

        else:
            cluster = self.log_cluster_cache.get(mask_id)
            cluster.size += 1
            self.drain.id_to_cluster[cluster.cluster_id]
            change_type = 'none'

        result = {
            'change_type': change_type,
            'cluster_id': cluster.cluster_id,
            'cluster_size': cluster.size,
            'template_mined': cluster.get_template(),
            'cluster_count': len(self.drain.clusters)
        }

        if self.persistence_handler is not None:
            self.profiler.start_section('save_state')
            snapshot_reason = self.get_snapshot_reason(change_type, cluster.cluster_id)
            if snapshot_reason:
                self.save_state(snapshot_reason)
                self.last_save_time = time.time()
            self.profiler.end_section()

        # self.profiler.end_section("total")
        self.profiler.report(self.config.profiling_report_sec)
        return result

    def add_log_message(self, log_message: str, log_service: str) -> dict:
        self.profiler.start_section('total')
        self.profiler.start_section('mask')
        masked_content = self.masker.mask(log_message)
        self.profiler.end_section()
        mask_id = self.log_cache.get(masked_content)
        if mask_id is None:
            self.id_to_log += 1
            self.log_cache[masked_content] = self.id_to_log

            self.profiler.start_section('drain')
            cluster, change_type = self.drain.add_log_message(masked_content, log_service)
            self.log_cluster_cache[self.id_to_log] = cluster
            self.profiler.end_section('drain')

        else:
            cluster = self.log_cluster_cache.get(mask_id)
            cluster.size += 1
            self.drain.id_to_cluster[cluster.cluster_id]
            change_type = 'none'

        result = {
            'change_type': change_type,
            'cluster_id': cluster.cluster_id,
            'cluster_size': cluster.size,
            'template_mined': cluster.get_template(),
            'cluster_count': len(self.drain.clusters)
        }

        if self.persistence_handler is not None:
            self.profiler.start_section('save_state')
            snapshot_reason = self.get_snapshot_reason(change_type, cluster.cluster_id)
            if snapshot_reason:
                self.save_state(snapshot_reason)
                self.last_save_time = time.time()
            self.profiler.end_section()

        self.profiler.end_section('total')
        self.profiler.report(self.config.profiling_report_sec)
        return result

    def match(self, log_message: str, full_search_strategy='never') -> LogCluster:
        """
        Mask log message and match against an already existing cluster.
        Match shall be perfect (sim_th=1.0).
        New cluster will not be created as a result of this call, nor any cluster modifications.

        :param log_message: log message to match
        :param full_search_strategy: when to perform full cluster search.
            (1) "never" is the fastest, will always perform a tree search [O(log(n)] but might produce
            false negatives (wrong mismatches) on some edge cases;
            (2) "fallback" will perform a linear search [O(n)] among all clusters with the same token count, but only in
            case tree search found no match.
            It should not have false negatives, however tree-search may find a non-optimal match with
            more wildcard parameters than necessary;
            (3) "always" is the slowest. It will select the best match among all known clusters, by always evaluating
            all clusters with the same token count, and selecting the cluster with perfect all token match and least
            count of wildcard matches.
        :return: Matched cluster or None if no match found.
        """

        masked_content = self.masker.mask(log_message)
        matched_cluster = self.drain.match(masked_content, full_search_strategy)
        return matched_cluster

    def get_parameter_list(self, log_template: str, log_message: str) -> List[str]:
        """
        Extract parameters from a log message according to a provided template that was generated
        by calling `add_log_message()`.

        This function is deprecated. Please use extract_parameters instead.

        :param log_template: log template corresponding to the log message
        :param log_message: log message to extract parameters from
        :return: An ordered list of parameter values present in the log message.
        """

        extracted_parameters = self.extract_parameters(log_template, log_message, exact_matching=False)
        if not extracted_parameters:
            return []
        return [parameter.value for parameter in extracted_parameters]

    def extract_parameters(self,
                           log_template: str,
                           log_message: str,
                           exact_matching: bool = True) -> Optional[List[ExtractedParameter]]:
        """
        Extract parameters from a log message according to a provided template that was generated
        by calling `add_log_message()`.

        For most accurate results, it is recommended that
        - Each `MaskingInstruction` has a unique `mask_with` value,
        - No `MaskingInstruction` has a `mask_with` value of `*`,
        - The regex-patterns of `MaskingInstruction` do not use unnamed back-references;
          instead use back-references to named groups e.g. `(?P=some-name)`.

        :param log_template: log template corresponding to the log message
        :param log_message: log message to extract parameters from
        :param exact_matching: whether to apply the correct masking-patterns to match parameters, or try to approximate;
            disabling exact_matching may be faster but may lead to situations in which parameters
            are wrongly identified.
        :return: A ordered list of ExtractedParameter for the log message
            or None if log_message does not correspond to log_template.
        """

        for delimiter in self.config.drain_extra_delimiters:
            log_message = re.sub(delimiter, ' ', log_message)

        template_regex, param_group_name_to_mask_name = self._get_template_parameter_extraction_regex(
            log_template, exact_matching)

        # Parameters are represented by specific named groups inside template_regex.
        parameter_match = re.match(template_regex, log_message)  # 从字符串log_message 开始匹配正则表达式template_regex，返回match对象

        # log template does not match template
        if not parameter_match:
            return None

        # create list of extracted parameters
        extracted_parameters = []
        for group_name, parameter in parameter_match.groupdict().items():
            if group_name in param_group_name_to_mask_name:
                mask_name = param_group_name_to_mask_name[group_name]
                extracted_parameter = ExtractedParameter(parameter, mask_name)
                extracted_parameters.append(extracted_parameter)

        return extracted_parameters

    @cachedmethod(lambda self: self.parameter_extraction_cache)
    def _get_template_parameter_extraction_regex(self, log_template: str, exact_matching: bool):
        param_group_name_to_mask_name = {}
        param_name_counter = [0]

        def get_next_param_name():
            param_group_name = 'p_' + str(param_name_counter[0])
            param_name_counter[0] += 1
            return param_group_name

        # Create a named group with the respective patterns for the given mask-name.
        def create_capture_regex(_mask_name):
            allowed_patterns = []
            if exact_matching:
                # get all possible regex patterns from masking instructions that match this mask name
                masking_instructions = self.masker.instructions_by_mask_name(_mask_name)
                for mi in masking_instructions:
                    # MaskingInstruction may already contain named groups.
                    # We replace group names in those named groups, to avoid conflicts due to duplicate names.
                    if hasattr(mi, 'regex'):
                        mi_groups = mi.regex.groupindex.keys()
                        pattern = mi.pattern
                    else:
                        # non regex masking instructions - support only non-exact matching
                        mi_groups = []
                        pattern = '.+?'

                    for group_name in mi_groups:
                        param_group_name = get_next_param_name()

                        def replace_captured_param_name(param_pattern):
                            _search_str = param_pattern.format(group_name)      # noqa
                            _replace_str = param_pattern.format(param_group_name)   # noqa
                            return pattern.replace(_search_str, _replace_str)      # noqa

                        pattern = replace_captured_param_name('(?P={}')
                        pattern = replace_captured_param_name('(?P<{}>')

                    # support unnamed back-references in masks (simple cases only)
                    pattern = re.sub(r'\\(?!0)\d{1,2}', r'(?:.+?)', pattern)
                    allowed_patterns.append(pattern)

            if not exact_matching or _mask_name == '*':
                allowed_patterns.append(r'.+?')

            # Give each capture group a unique name to avoid conflicts.
            param_group_name = get_next_param_name()
            param_group_name_to_mask_name[param_group_name] = _mask_name
            joined_patterns = '|'.join(allowed_patterns)
            capture_regex = f'(?P<{param_group_name}>{joined_patterns})'
            return capture_regex

        # For every mask in the template, replace it with a named group of all
        # possible masking-patterns it could represent (in order).
        mask_names = set(self.masker.mask_names)

        # the Drain catch-all mask
        mask_names.add('*')

        escaped_prefix = re.escape(self.masker.mask_prefix)
        escaped_suffix = re.escape(self.masker.mask_suffix)
        template_regex = re.escape(log_template)

        # replace each mask name with a proper regex that captures it
        for mask_name in mask_names:
            search_str = escaped_prefix + re.escape(mask_name) + escaped_suffix
            while True:
                rep_str = create_capture_regex(mask_name)
                # Replace one-by-one to get a new param group name for each replacement.
                template_regex_new = template_regex.replace(search_str, rep_str, 1)
                # Break when all replaces for this mask are done.
                if template_regex_new == template_regex:
                    break
                template_regex = template_regex_new

        # match also messages with multiple spaces or other whitespace chars between tokens
        template_regex = re.sub(r'\\ ', r'\\s+', template_regex)
        template_regex = '^' + template_regex + '$'
        return template_regex, param_group_name_to_mask_name

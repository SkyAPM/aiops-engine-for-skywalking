#  Copyright 2022 SkyAPM org
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
This script is used by Makefile to download the testing datasets
or simply for curious inspection of sample data.
"""
import functools
import os
import pathlib
import shutil
import tarfile
import typing
import zipfile

import requests
from tqdm import tqdm

TARGET_DIR_BASE = pathlib.Path('assets') / 'datasets'
os.makedirs(TARGET_DIR_BASE, exist_ok=True)


def download_file(url: str, target_dir: typing.Union[str, bytes, os.PathLike]):
    """
    Downloads dataset from url to target_dir
    :param target_dir:
    :param url: URL to download the file
    :return: the path to the downloaded file
    """
    local_filename = url.split('/')[-1]
    target_path = os.path.join(target_dir, local_filename)
    with requests.get(url, stream=True) as res:
        total_size: int = int(res.headers.get('content-length', 0))
        desc = '(Unknown size)' if total_size == 0 else f'Total size {total_size / 1024 / 1024:.2f} MB'
        res.raw.read = functools.partial(res.raw.read, decode_content=True)  # Decompress if needed
        with tqdm.wrapattr(res.raw, 'read', total=total_size, desc=desc) as r_raw:
            with pathlib.Path(target_path).open('wb') as f:
                shutil.copyfileobj(r_raw, f)

    return local_filename


def extract(path_to_file: typing.Union[str, bytes, os.PathLike],
            target_dir: typing.Union[str, bytes, os.PathLike]) -> None:
    """
    extract the dataset to a path
    :param path_to_file: path to the zip file
    :param target_dir: path to the target directory
    :return: the path to the unzipped file
    """
    if zipfile.is_zipfile(path_to_file):
        with zipfile.ZipFile(path_to_file, 'r') as zip_ref:
            zip_ref.extractall(path=target_dir)
    elif tarfile.is_tarfile(path_to_file):
        with tarfile.open(path_to_file) as tar:
            tar.extractall(path=target_dir)
    else:
        raise ValueError('Unknown file type')


def get_gaia():
    """
    Download the full Gaia dataset
    :return: the path to the downloaded file
    """
    gaia_url_base = 'https://github.com/CloudWise-OpenSource/GAIA-DataSet/archive/refs/heads/main.zip'
    print('Downloading GAIA dataset, it may take a while...')
    download_file(url=gaia_url_base, target_dir=TARGET_DIR_BASE)

    extract(path_to_file=pathlib.Path(TARGET_DIR_BASE) / 'main.zip',
            target_dir=pathlib.Path(TARGET_DIR_BASE) / 'gaia_datasets')


def get_loghub(size: str = 'small'):
    # https://zenodo.org/record/3227177/#.YsdGBRXMJD8 << Datasets
    base_url = 'https://zenodo.org/record/3227177/files/'

    small_data_list = ['SSH.tar.gz', 'Hadoop.tar.gz', 'Apache.tar.gz',
                       'HealthApp.tar.gz', 'Zookeeper.tar.gz', 'HPC.tar.gz']
    medium_data_list = ['Android.tar.gz', 'BGL.tar.gz', 'Spark.tar.gz']
    large_data_list = ['HDFS_2.tar.gz', 'Thunderbird.tar.gz']
    data_list = []
    if size == 'small':
        data_list = small_data_list
    elif size == 'medium':
        data_list = medium_data_list
    elif size == 'large':
        data_list = large_data_list
    for dataset in data_list:
        print(f'Downloading {dataset}')
        target_dir = TARGET_DIR_BASE / 'loghub_datasets' / size
        os.makedirs(target_dir, exist_ok=True)
        download_file(url=base_url + dataset, target_dir=target_dir)
        print(f'Extracting {dataset}')
        extract(path_to_file=target_dir / dataset, target_dir=target_dir / dataset.replace('.tar.gz', ''))


def clean(purge: bool = False):
    """
    Clean the assets folder
    :return: None
    """
    if purge:
        print(f'Purging {TARGET_DIR_BASE}')
        shutil.rmtree(TARGET_DIR_BASE)
    else:
        for root, _, files in os.walk(TARGET_DIR_BASE):
            for file in files:
                if file.endswith('.zip') or file.endswith('.tar.gz'):
                    os.remove(os.path.join(root, file))


if __name__ == '__main__':
    import argparse


    def parse():
        parser = argparse.ArgumentParser(prog='get_data')
        subparsers = parser.add_subparsers(help='sub-command help', dest='command_name')

        # help to clean the assets folder
        parser_clean = subparsers.add_parser('clean', help='To clean the dataset folder')
        parser_clean.add_argument('-p', '--purge', action='store_true',
                                  help='to entirely remove compressed and also extracted data files')

        # help to download different datasets
        parser_download = subparsers.add_parser('download', help='Dataset name to download')
        parser_download.add_argument('-n', '--name', help='what data do you need?')
        parser_download.add_argument('-s', '--save', type=bool, default=False,
                                     help="don't delete the compressed datasets")

        cmd_args = parser.parse_args()

        return cmd_args


    args = parse()
    possible_datasets = ['gaia', 'log_s', 'log_m', 'log_l']
    if args.command_name == 'clean':
        clean(purge=True) if args.purge else clean(purge=False)
    elif args.command_name == 'download':
        print('Download starting...')
        if args.name in possible_datasets:
            if args.name == 'gaia':
                get_gaia()
            elif args.name == 'log_s':
                get_loghub(size='small')
            elif args.name == 'log_m':
                get_loghub(size='medium')
            elif args.name == 'log_l':
                get_loghub(size='large')
        if not args.save:
            clean(purge=False)

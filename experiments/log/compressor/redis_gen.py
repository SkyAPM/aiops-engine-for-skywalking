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

import time

from pyzstd import train_dict, ZstdCompressor

in_log_file = 'hadoop-hdfs-datanode-mesos-28.log'

import sys

from redis import Redis


def get_lines():
	with open(in_log_file) as f:
		for each_line in f:
			yield each_line


# @timing(repeat=10)
def send_data(redis_connection, max_messages: int, batch_size: int):
	count = 0
	total = 0
	total_log_size = 0
	pipeline = redis_connection.pipeline(transaction=False)  # set no transaction
	log_gen = get_lines()

	def train_zstd():
		with open(file='training_dict_samples.txt', mode='br') as train_in:
			zstd_dict = train_dict(samples=train_in, dict_size=10 ** 6)
		# print('done training dict on first 5000 log samples')
		return zstd_dict

	zstd_compressor = ZstdCompressor(zstd_dict=train_zstd())
	while total < max_messages:
		total += 1
		count += 1
		try:
			next_log = next(log_gen)
		except StopIteration:
			print('reached end of log file with total', total)
			return

		zstd_compressor.compress(bytes(next_log, encoding='utf-8'))
		log_compressed = zstd_compressor.flush()
		data = {
			'log_compressed': log_compressed,
			# FIXME TEST DEFAULT = 6 AND ZSTD TEST MASK SPEED
			# Just some sample logs without considering line breaks
			'service': 'agent::recommendation213131',
		}
		total_log_size += sys.getsizeof(data['log_compressed']) / 1024
		pipeline.xadd('test', data)
		if count == batch_size:
			# send the pipeline
			count = 0
			resp = pipeline.execute()
	if count != 0:
		resp = pipeline.execute()
	print(f'size of log in Mega byte {total_log_size / 1024:2f}MB')


def main(count: int, batch_size: int):
	def connect_to_redis():
		hostname = 'localhost'
		port = 49153
		conn = Redis(hostname, port, retry_on_timeout=True, username='default', password='redispw')

		return conn

	conn = connect_to_redis()
	conn.delete('test')

	# batch producer to stream
	start = time.time()
	send_data(conn, count, batch_size=batch_size)
	end = time.time()
	print(f'Time taken to send 500k messages with batch {batch_size}: {end - start} seconds')


# conn.delete('test')


if __name__ == '__main__':
	main(count=500000, batch_size=2000)

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

VERSION ?= latest

# determine host platform
VENV_DIR = .venv
VENV = $(VENV_DIR)/bin
ifeq ($(OS),Windows_NT)
    VENV=./$(VENV_DIR)/Scripts
endif

$(VENV):
	python3 -m venv $(VENV_DIR)
	poetry run python -m pip install --upgrade pip
	poetry install --sync

all: gen get-dataset prune-dataset lint license clean

.PHONY: all

gen:
	poetry run python -m tools.grpc_gen

#argument indicates a dataset name defined in sample_data_manager.py
get-dataset:
	poetry run python -m tools.sample_data_manager download --name $(name) --save $(save)
prune-dataset: # remove all downloaded datasets
	poetry run python -m tools.sample_data_manager clean --purge

# flake8 configurations should go to the file setup.cfg

lint-setup:
	poetry install --only linters

lint: lint-setup
	poetry run python -m flake8

# fix problems described in CodingStyle.md - verify outcome with extra care
lint-fix: lint-setup
	$(VENV)/isort .
	$(VENV)/unify -r --in-place .
	$(VENV)/flynt -tc -v .

clean:
	poetry run python -m tools.cleaner

#!/bin/bash

docker run \
       -it --rm \
       --network host \
       -v `pwd`:/aider \
       -v `pwd`/tmp.benchmarks/.:/benchmarks \
       -e OPENAI_API_KEY=$OPENAI_API_KEY \
       -e HISTFILE=/aider/.bash_history \
       -e PROMPT_COMMAND='history -a' \
       -e HISTCONTROL=ignoredups \
       -e HISTSIZE=10000 \
       -e HISTFILESIZE=20000 \
       -e AIDER_DOCKER=1 \
       -e AIDER_BENCHMARK_DIR=/benchmarks \
       aider-benchmark \
       bash

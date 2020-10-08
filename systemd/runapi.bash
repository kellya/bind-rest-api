#!/bin/bash

export HOME=/home/bind-rest-api

# Pyenv
export PATH="/home/bind-rest-api/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

source $HOME/bind-rest-api/config.env

pyenv activate bind

cd $HOME/bind-rest-api
uvicorn bindapi:app


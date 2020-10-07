#!/usr/bin/fish

export HOME=/root

# Pyenv - after poetry to fix oddness
if test -d "$HOME/.pyenv/bin"
  if not echo $PATH | grep -q $HOME/.pyenv/bin
                set PATH $HOME/.pyenv/bin $PATH
        end
  source (pyenv init - fish | psub)
end

export (cat /root/bind-rest-api/config.env)

pyenv activate bind2

cd /root/bind-rest-api
echo $BIND_SERVER
uvicorn bindapi:app


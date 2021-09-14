# bind-rest-api

This is a BIND API that allows the following functionality:
* dumping the zone file to JSON
* GETting a specific DNS record
* POSTing to create a new DNS record
* PUTing to replace a DNS record
* DELETEing a DNS record

This project is inspired by [https://github.com/dmyerscough/BIND-RESTful](https://github.com/dmyerscough/BIND-RESTful)

But it adds extra functionality, including:
* using [FastAPI](https://fastapi.tiangolo.com/) instead of Flask as the framwork, which allows:
  * auto-generated API docs and tooling
  * full input validation
* API Key protection (but still definitely don't expose this to the internet)
* Audit log of `apikey` ➡ `DNS changes`
* [acme.sh](https://acme.sh) tooling to generate LetsEncrypt certificates using the API
* Docker container to make it easier to run: https://hub.docker.com/r/jaytuckey/bind-rest-api

## Auto-generated docs

By using FastAPI this project get's auto-generated Swagger-UI docs:
![auto docs 1](img/bind-rest-api-01.png)

![auto docs 2](img/bind-rest-api-02.png)

## Getting set up and running

I have made a video of myself setting up the project: https://youtu.be/ZNEtmWhu1HI

* Clone the bind-rest-api repo locally, and cd into your clone.
* Make sure you have python 3 and [poetry](https://python-poetry.org/) installed.
* From within the bind-rest-api clone, run `poetry install` to install all the required dependencies.
  * Poetry will try to install into a virtualenv
  * You can activate the auto-created virtualenv with `poetry shell`
  * Once actived you should see the dependencies with `pip list`. Make sure you see lines like:
  ```
  dnspython         2.0.0
  fastapi           0.61.1
  ```

### BIND Server Setup

bind-rest-api utilizes BIND's TSIG functionailty to validate dynamic updates.
The first step is to generate a TSIG key on the BIND server, and configure the
server to use that key.

1. On the bind server, navigate to your named configuration dir.  On Fedora,
   this is `/etc/named` other distros may be different.
2. Generate a keyfile with `tsig-keygen bindapi > bindapi.tsig`.  the "bindapi" part can be
   whatever you choose, this is they name of the key and will be what you will
   use in bind-rest-api's config as the username.
3. edit your named.conf (probably /etc/named.conf) to include the key that was
   just generated.  At the top add `include "/etc/named/bindapi.tsig` (alter if
   your directory in the first step is not /etc/named).
4. Restart named to make the new configuration take effect `systemctl restart
   named.service`


### bind-rest-api configuration

With the BIND Server Setup complete, you may now edit the bind-rest-api
configuration to connect the two together.

1. Copy the example_config.env to config.env `cp example_config.env config.env`
2. Edit the config.env
    `BIND_SERVER` - Set this to your BIND server's name or IP

    `TSIG_USERNAME` - This will be the keyname from the bindapi.tsig generated
    in the "BIND Server Setup" above

    `TSIG_PASSWORD` - this is the "secret" value from the bindapi.tsig file
    genereated in the "BIND Server Setup" above.

    `BIND_ALLOWED_ZONES` - Comma separated list of zones that bind-rest-api
    should be allowed to modify.

    `API_KEY_FILE` - This will be used for the API access.  The default is fine,
    and that's what we are going to do in step 3.
3. Copy the example_apikeys.pass to apikeys.pass `mv example_apikeys.pass
   apikeys.pass`
4. edit apikeys.pass to set appropriate values.  This is a comma separated
   values key/value pair of keyname and keypass.  Keyname will be used in
   logging to show what key has made modifications, and the keypass will be the
   secret/auth token used to authenticate the key.  These can be anything you
   choose.  For a secure password, it would be a good idea to use a long random
   string for the keypass.  You could generate one with something like `openssl
   rand -hex 32`

### running bind-rest-api

1. export the values in config.env to your shell `export $(cat config.env)`
2. run the bindapi.py CLI `bindapi.py`.  If all is successful, you should see
   something like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [35934] using statreload
INFO:     Started server process [35940]INFO:     Waiting for application startup.INFO:     Application startup complete.
```

This has started on localhost port 8000 by default.  If you are running on a
diffrent host than you are accessing the API from, you will need to bind to a
different IP address.  Instead you may start with:

`bindapi.py --host 0.0.0.0`
That will listen on all IP addresses (again, on the default port 8000)

3.  Finally, browse to whatever Uvicorn is running on /docs. Assuming localhost,
    that means [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

At this point you should see FastAPI's swagger documentation where you can hit
the "Authorize" button, and enter the password you put in apikeys.pass above and
test it out.



### Keys and Flow
There are two flows that need keys:

`HTTP Clients --> API` and `API --> bind9`

#### `HTTP Clients --> API`
These clients use an `X-Api-Key` HTTP header when performing requests. The API confirms that the key provided is in the `apikeys.pass` file, and then logs the friendly name for that api key.

#### `API --> bind9`
To send updates to the bind9 server the API uses a TSIG key. You put this TSIG username/password in the `config.env` file, and then also reference it in the bind9 configuration. For full details see the bind9 docs: https://bind9.readthedocs.io/en/v9_16_9/advanced.html#tsig

To test your TSIG key you can use the `nsupdate` tool: https://bind9.readthedocs.io/en/v9_16_9/manpages.html#man-nsupdate

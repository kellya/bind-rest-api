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
* [acme.sh](https://acme.sh) tooling to generate LetsEncrypt certificates using the API

## Auto-generated docs

By using FastAPI this project get's auto-generated Swagger-UI docs:
![auto docs 1](img/bind-rest-api-01.png)

![auto docs 2](img/bind-rest-api-02.png)

## Getting set up and running

* Make sure you have python 3 and [poetry](https://python-poetry.org/) installed.
* From within the folder, run `poetry install` to install all the required dependencies.
* copy the `example_config.env` and `example_apikeys.pass` files to `config.env` and `apikeys.pass`
* Customise the files and set the values you need. Make sure to generate very long api keys.
* export all the environment variables in `config.env`
* run the api with uvicorn - `uvicorn bindapi:app`


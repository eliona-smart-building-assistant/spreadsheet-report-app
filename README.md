# eliona_Karla_Kolumna

Create Report files from eliona with the official eliona public api

## Development Dokumentation

https://wiki.leicom.ch/books/eliona-energiereporting-plugin

## Repository 

https://gitlab.leicom.ch/pm/eliona_karla_kolumna

## Create your development environment

Create your virtual python environment. Use Python 3.10.6

> python3 -m venv env

activate your environment

> source env/bin/activate

Install the needed modules

> python -m pip install -r requirements.txt

In order to install the requirements there is an tokken vom the support user used. 

## Build the docker container

Within the repo path enter this cmd. Please note the . at the end of the command. 
This needed to be add.

> docker build --tag eliona-karla-kolumna .

## Run the docker container

Within the repo path enter this cmd.

> docker run eliona-karla-kolumna



eliona page to test the api:
https://eliona-smart-building-assistant.github.io/open-api-docs/?https://raw.githubusercontent.com/eliona-smart-building-assistant/eliona-api/develop/openapi.yaml#/Data/getDataAggregated

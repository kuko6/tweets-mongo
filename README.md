# Mongo tweets

This repository includes: 
- python scripts and sql queries used for denormalizing and exporting postgres database of tweets and importing them into mongodb

## Usage

Install the requirements:
```
pip install -r requirements.txt
```

Configure the database connection in the `config/connect.py` file and run the main script:
```
python3 ./src/main.py
```

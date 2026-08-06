## 0.3.1 (2026-07-17)

### Fix

- initial schema for aquariums

## 0.3.0 (2026-07-16)

### Feat

- add user persistence

## 0.2.3 (2026-07-16)

### Fix

- some naming inconsistencies

## 0.2.2 (2026-07-16)

### Fix

- update pytest

## 0.2.1 (2026-07-16)

### Fix

- bump dependencies

## 0.2.0 (2026-07-16)

### Feat

- add database storage backend

### Fix

- bump dependencies

## 0.1.1 (2026-07-12)

### Fix

- dependency cleanup

## 0.1.0 (2026-07-12)

### Feat

- update tooling
- standardise dependencies
- auth
- add example compose file
- add dockerfile for deployment
- added test-coverage reports
- add test results to server
- salinity dosing calculator
- initial project framework

### Fix

- bump uvicorn from 0.35.0 to 0.51.0
- bump pytest-html from 4.1.1 to 4.2.0
- remove redundant main.py

## v0.13.2 (2026-08-06)

### Fix

- bump cryptography in the pip group across 1 directory

## v0.13.1 (2026-08-02)

### Refactor

- organised the code

## v0.13.0 (2026-08-01)

### Feat

- add configurable auth mode (oauth/none)

### Fix

- update taskfile with new fake-auth

## v0.12.1 (2026-08-01)

### Fix

- add missing data to params and units

## v0.12.0 (2026-07-31)

### Feat

- back measurement units with a DB catalog and parameter-unit associations

### Fix

- some public endpoints
- correct units symbols
- split Unit slug (URL-safe) from unit notation

## v0.11.0 (2026-07-31)

### Feat

- add parameter list to database

## v0.10.1 (2026-07-31)

### Fix

- replace deprecated pydantic .dict() with model_dump()

## v0.10.0 (2026-07-27)

### Feat

- additional parameters for measurements

## v0.9.0 (2026-07-27)

### Feat

- parameter thresholds

### Fix

- cleaner handling of database connection errors
- dockerfile poetry broken, switching to requirements.txt
- poetry container

## v0.8.2 (2026-07-26)

### Fix

- bump httpx2 from 2.7.0 to 2.9.1

## v0.8.1 (2026-07-26)

### Fix

- decouple auth issuer from discovery URL

## v0.8.0 (2026-07-24)

### Feat

- add app_version to API

## v0.7.1 (2026-07-24)

### Fix

- update container with security updates
- update mail-relay container with security updates
- refactor DB credentials to separate fields
- make the DB password a SecretStr to prevent log leakage.

## v0.7.0 (2026-07-24)

### Feat

- additional delete endpoint for params
- add phosphate measurements
- add mail smtp-to-api proxy
- add measurement endpoints
- add user persistence
- add database storage backend
- update tooling
- standardise dependencies

### Fix

- first pass at linting
- improve startup process for dev
- bump obsolete httpx and authlib modules
- small fixes to test scripts
- pipeline error in mail relay builder
- bump fastapi from 0.139.1 to 0.139.2
- update build pipeline with new scripts
- increase logging capability
- add favicon
- move docs to versioned url
- updated build
- updated build
- updated build
- updated build
- updated build
- testing build pipeline
- initial schema for aquariums
- some naming inconsistencies
- update pytest
- bump dependencies
- dependency cleanup
- bump uvicorn from 0.35.0 to 0.51.0
- bump pytest-html from 4.1.1 to 4.2.0

## v0.6.0 (2026-07-22)

### Feat

- additional delete endpoint for params
- add phosphate measurements

### Fix

- bump obsolete httpx and authlib modules
- small fixes to test scripts

## v0.5.1 (2026-07-21)

### Fix

- pipeline error in mail relay builder

## v0.5.0 (2026-07-21)

### Feat

- add mail smtp-to-api proxy

## v0.4.2 (2026-07-19)

### Fix

- bump fastapi from 0.139.1 to 0.139.2

## v0.4.1 (2026-07-19)

### Fix

- update build pipeline with new scripts

## v0.4.0 (2026-07-19)

### Feat

- add measurement endpoints

## v0.3.10 (2026-07-18)

### Fix

- increase logging capability

## v0.3.9 (2026-07-18)

### Fix

- add favicon

## v0.3.8 (2026-07-18)

### Fix

- move docs to versioned url

## v0.3.7 (2026-07-17)

### Fix

- updated build

## v0.3.6 (2026-07-17)

### Fix

- updated build

## v0.3.5 (2026-07-17)

### Fix

- updated build

## v0.3.4 (2026-07-17)

### Fix

- updated build

## v0.3.3 (2026-07-17)

### Fix

- updated build

## v0.3.2 (2026-07-17)

## v0.3.1 (2026-07-17)

### Fix

- testing build pipeline
- initial schema for aquariums

## v0.3.0 (2026-07-16)

## v0.2.3 (2026-07-16)

### Feat

- add user persistence

## v0.2.2 (2026-07-16)

### Fix

- some naming inconsistencies
- update pytest

## v0.2.1 (2026-07-16)

## v0.2.0 (2026-07-16)

### Feat

- add database storage backend

### Fix

- bump dependencies

## v0.1.1 (2026-07-12)

### Fix

- dependency cleanup

## v0.1.0 (2026-07-12)

### Feat

- update tooling
- standardise dependencies
- auth
- add example compose file
- add dockerfile for deployment
- added test-coverage reports
- add test results to server
- salinity dosing calculator
- initial project framework

### Fix

- bump uvicorn from 0.35.0 to 0.51.0
- bump pytest-html from 4.1.1 to 4.2.0
- remove redundant main.py

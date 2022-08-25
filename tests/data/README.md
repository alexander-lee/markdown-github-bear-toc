[![Build Status](https://app.travis-ci.com/NCI-GDC/plaster.svg?token=5s3bZRahNJnkspYEMwZC&branch=master)](https://app.travis-ci.com/NCI-GDC/plaster)

# The Data Commons Model Source Generator Project (Plaster)

GDC internship project for generating data model source code.

<!-- toc -->

- [Purpose](#purpose)
- [Goal](#goal)
- [Data Commons Models](#data-commons-models)
  - [Problems:](#problems)
- [Project Details](#project-details)
  - [Requirements](#requirements)
  - [Features](#features)
  - [Dictionary selection and loading](#dictionary-selection-and-loading)
  - [Template Management](#template-management)
- [How to use](#how-to-use)
  - [Install plaster](#install-plaster)
  - [Generate gdcdictionary](#generate-gdcdictionary)
  - [Generate biodictionary](#generate-biodictionary)
- [Associated Projects](#associated-projects)

<!-- tocstop -->

# Purpose

This project is a drop-in replacement to the project
https://github.com/NCI-GDC/gdcdatamodel, without challenges and obscurity associated
with using gdcdatamodel. The resulting code will be readable, pass static and linting
checks, completely remove delays from dictionary load times.

# Goal

Given any compliant gdcdictionary, generate source code that can replace the
gdcdatamodel runtime generated code.

# Data Commons Models

The data commons are a collection of data structures representing concepts within a
subject area. These data structures usually form a graph with edges as relationships to
one another. The data structures and relationships are defined as JSON schema in yaml
files that are distributed via a git repository. These definitions are called
Dictionaries for short. The gdcdictionary is one example of a data commons with a
primarily focus on cancer. Dictionaries are updated and released frequently, with each
release adding or removing nodes, edges, or properties.

These data structures are converted to Python source code at runtime by the gdcdatamodel
project. For example, the case yaml file will autogenerate the models.Case Python class
with properties and methods matching those defined in the yaml file. The generated
source codes are sqlalchemy database entities that map to tables in the database.

The psqlgraph project makes querying using these entities more uniform across different
use cases, by exposing common modules, classes and functions that are useful for
manipulating data stored using sqlalchemy.

## Problems:

- Runtime generated code cannot be peer reviewed or inspected. This forces developers to
  switch between dictionary definitions and code to understand what a particular piece
  of code is doing. Most projects within the center have this problem since they all
  rely on gdcdatamodel for the database entities.
- Runtime generated code also means no type checking, linting and little chance of
  running static analysis tools like flake8
- Runtime model code generation takes a few seconds (might be a few minutes - Qiao) to
  complete. This means that any project that makes use of gdcdatamodel must pay for this
  in one way or another. The most common is usually start up time.

In summary, most projects within the center suffer just because they rely on
gdcdatamodel for database entities. The major goal of this project is to eliminate the
runtime code generation feature on gdcdatamodel, thereby eliminating the above-mentioned
problems.

# Project Details

## Requirements

- Python >= 3.8
- No direct dependency on any dictionary versions
- Must expose scripts that can be invoked to generate source code
- Must include unit and integration tests with over 80% code coverage
- Must provide typings and pass mypy checks

## Features

- Dictionary selection and loading
- Template management
- Code generation
- Scripts

## Dictionary selection and loading

This module will be responsible for loading a dictionary given necessary parameters.
These parameters will include:

- A git URL
- A target version, tag, commit or branch name
- A label used for referencing the dictionary later

## Template Management

This module will be responsible for the templates used to generate the final source code

# How to use

## Install plaster

```bash
pip install .
```

## Generate gdcdictionary

```bash
plaster generate -p gdcdictionary -o "example/gdcdictionary"
```

## Generate biodictionary

```bash
plaster generate -p biodictionary -o "example/biodictionary"
```

# Associated Projects

- biodictionary: https://github.com/NCI-GDC/biodictionary
- gdcdatamodel: https://github.com/gdcdatamodel
- gdcdictionary: https://github.com/NCI-GDC/gdcdictionary
- psqlgml: https://github.com/NCI-GDC/psqlgml
- psqlgraph: https://github.com/NCI-GDC/psqlgraph

# Repo Visualizer

![Visualization of this repo](images/diagram.svg)

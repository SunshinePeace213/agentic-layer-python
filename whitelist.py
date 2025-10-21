#!/usr/bin/env python3
# ruff: noqa
# type: ignore
"""
Vulture Whitelist - Common False Positives
==========================================
This file contains common patterns that vulture incorrectly flags as dead code.
Use with: vulture yourcode.py whitelist.py

NOTE: This file intentionally contains "undefined" names and "unused" imports
      as these are patterns we want vulture to ignore in actual code.
      
Categories:
1. Testing Framework Patterns
2. Web Framework Patterns
3. CLI Framework Patterns
4. Protocol/Interface Methods
5. Type Checking Patterns
6. Magic Methods
7. Hook/Callback Patterns
8. Intentionally Unused Variables
"""

# ============================================================================
# TESTING FRAMEWORK PATTERNS
# ============================================================================

# Pytest fixtures and hooks
def pytest_configure(config):  # pytest hook
    pass

def pytest_collection_modifyitems(config, items):  # pytest hook
    pass

def pytest_runtest_setup(item):  # pytest hook
    pass

def pytest_runtest_teardown(item):  # pytest hook
    pass

def pytest_fixture_setup(fixturedef, request):  # pytest hook
    pass

# Common test class methods
class TestCase:
    def setUp(self):  # unittest setup
        pass
    
    def tearDown(self):  # unittest teardown
        pass
    
    def setUpClass(cls):  # unittest class setup
        pass
    
    def tearDownClass(cls):  # unittest class teardown
        pass
    
    def setUpModule():  # unittest module setup
        pass
    
    def tearDownModule():  # unittest module teardown
        pass

# Test discovery patterns
def test_():  # test function prefix
    pass

class Test_:  # test class prefix
    pass

# ============================================================================
# WEB FRAMEWORK PATTERNS
# ============================================================================

# Flask patterns
@app.route  # Flask route decorator
def route_handler():
    pass

@app.before_request  # Flask hook
def before_request():
    pass

@app.after_request  # Flask hook
def after_request(response):
    pass

@app.errorhandler  # Flask error handler
def error_handler(error):
    pass

@app.template_filter  # Flask template filter
def template_filter():
    pass

# Django patterns
class DjangoView:
    def get(self, request):  # Django GET handler
        pass
    
    def post(self, request):  # Django POST handler
        pass
    
    def put(self, request):  # Django PUT handler
        pass
    
    def delete(self, request):  # Django DELETE handler
        pass
    
    def dispatch(self, request):  # Django dispatcher
        pass

# Django model methods
class DjangoModel:
    def save(self):  # Django model save
        pass
    
    def delete(self):  # Django model delete
        pass
    
    def clean(self):  # Django model validation
        pass
    
    def full_clean(self):  # Django model full validation
        pass

# FastAPI patterns
@app.get  # FastAPI GET endpoint
@app.post  # FastAPI POST endpoint
@app.put  # FastAPI PUT endpoint
@app.delete  # FastAPI DELETE endpoint
@app.patch  # FastAPI PATCH endpoint
def fastapi_endpoint():
    pass

# ============================================================================
# CLI FRAMEWORK PATTERNS
# ============================================================================

# Click patterns
@click.command  # Click command
@click.group  # Click group
@click.option  # Click option
@click.argument  # Click argument
def cli_command():
    pass

# Argparse patterns
parser.add_argument  # argparse argument
parser.add_subparsers  # argparse subparsers
parser.set_defaults  # argparse defaults

# Fire patterns (Google Python Fire)
def main():  # Common CLI entry point
    pass

# ============================================================================
# PROTOCOL/INTERFACE METHODS
# ============================================================================

# Context manager protocol
class ContextManager:
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

# Async context manager protocol
class AsyncContextManager:
    async def __aenter__(self):
        pass
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# Iterator protocol
class Iterator:
    def __iter__(self):
        pass
    
    def __next__(self):
        pass

# Async iterator protocol
class AsyncIterator:
    def __aiter__(self):
        pass
    
    async def __anext__(self):
        pass

# Descriptor protocol
class Descriptor:
    def __get__(self, obj, objtype=None):
        pass
    
    def __set__(self, obj, value):
        pass
    
    def __delete__(self, obj):
        pass

# ============================================================================
# TYPE CHECKING PATTERNS
# ============================================================================

# Type checking imports (often unused at runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import (
        Any,
        Dict,
        List,
        Optional,
        Union,
        Tuple,
        Set,
        Callable,
        TypeVar,
        Generic,
        Protocol,
        TypedDict,
        Literal,
        Final,
        ClassVar,
        cast,
        overload,
    )

# Forward reference patterns
from __future__ import annotations

# Type aliases
JsonDict = Dict[str, Any]  # type alias
OptionalStr = Optional[str]  # type alias

# Protocol definitions
class Comparable(Protocol):
    def __lt__(self, other) -> bool:
        pass
    
    def __le__(self, other) -> bool:
        pass
    
    def __gt__(self, other) -> bool:
        pass
    
    def __ge__(self, other) -> bool:
        pass

# ============================================================================
# MAGIC METHODS
# ============================================================================

class MagicMethods:
    # Object creation and destruction
    def __new__(cls):
        pass
    
    def __init__(self):
        pass
    
    def __del__(self):
        pass
    
    # String representations
    def __str__(self):
        pass
    
    def __repr__(self):
        pass
    
    def __format__(self, format_spec):
        pass
    
    def __bytes__(self):
        pass
    
    # Comparison operators
    def __eq__(self, other):
        pass
    
    def __ne__(self, other):
        pass
    
    def __lt__(self, other):
        pass
    
    def __le__(self, other):
        pass
    
    def __gt__(self, other):
        pass
    
    def __ge__(self, other):
        pass
    
    # Arithmetic operators
    def __add__(self, other):
        pass
    
    def __sub__(self, other):
        pass
    
    def __mul__(self, other):
        pass
    
    def __truediv__(self, other):
        pass
    
    def __floordiv__(self, other):
        pass
    
    def __mod__(self, other):
        pass
    
    def __pow__(self, other):
        pass
    
    # Container methods
    def __len__(self):
        pass
    
    def __getitem__(self, key):
        pass
    
    def __setitem__(self, key, value):
        pass
    
    def __delitem__(self, key):
        pass
    
    def __contains__(self, item):
        pass
    
    # Attribute access
    def __getattr__(self, name):
        pass
    
    def __setattr__(self, name, value):
        pass
    
    def __delattr__(self, name):
        pass
    
    def __getattribute__(self, name):
        pass
    
    # Callable
    def __call__(self):
        pass
    
    # Copying
    def __copy__(self):
        pass
    
    def __deepcopy__(self, memo):
        pass
    
    # Pickle support
    def __getstate__(self):
        pass
    
    def __setstate__(self, state):
        pass
    
    def __reduce__(self):
        pass
    
    def __reduce_ex__(self, protocol):
        pass

# ============================================================================
# HOOK/CALLBACK PATTERNS
# ============================================================================

# Common hook names
def on_start():
    pass

def on_stop():
    pass

def on_connect():
    pass

def on_disconnect():
    pass

def on_message(message):
    pass

def on_error(error):
    pass

def on_close():
    pass

def on_open():
    pass

# Event handlers
def handle_event(event):
    pass

def process_message(message):
    pass

def validate_data(data):
    pass

# Lifecycle hooks
def initialize():
    pass

def finalize():
    pass

def setup():
    pass

def cleanup():
    pass

# ============================================================================
# INTENTIONALLY UNUSED VARIABLES
# ============================================================================

# Common unused variable patterns
_ = None  # Underscore for intentionally unused
__ = None  # Double underscore for intentionally unused
_unused = None  # Explicitly marked unused
dummy = None  # Dummy variable

# Loop variables
for _ in range(10):  # Unused loop variable
    pass

for _index, value in enumerate([]):  # Unused index
    pass

for key, _ in {}.items():  # Unused value
    pass

# Exception handling
try:
    pass
except Exception as _:  # Unused exception
    pass

# Function arguments
def callback(arg1, arg2, *args, **kwargs):  # Common callback signature
    pass

def handler(sender, **kwargs):  # Django signal handler
    pass

def middleware(request, get_response):  # Django middleware
    pass

# ============================================================================
# ABSTRACT BASE CLASS PATTERNS
# ============================================================================

from abc import ABC, abstractmethod

class AbstractBase(ABC):
    @abstractmethod
    def abstract_method(self):  # Must be implemented by subclasses
        pass
    
    @abstractmethod
    def process(self):  # Common abstract method name
        pass
    
    @abstractmethod
    def execute(self):  # Common abstract method name
        pass
    
    @abstractmethod
    def run(self):  # Common abstract method name
        pass

# ============================================================================
# LOGGING PATTERNS
# ============================================================================

import logging

logger = logging.getLogger(__name__)  # Common logger pattern
log = logging.getLogger(__name__)  # Alternative logger name
LOG = logging.getLogger(__name__)  # Uppercase logger

# Logging methods often look unused
logger.debug
logger.info
logger.warning
logger.error
logger.critical
logger.exception

# ============================================================================
# DJANGO SPECIFIC PATTERNS
# ============================================================================

# Django migrations
class Migration:
    dependencies = []  # Django migration dependencies
    operations = []  # Django migration operations
    
    def forwards(self, apps, schema_editor):  # Migration forward
        pass
    
    def backwards(self, apps, schema_editor):  # Migration backward
        pass

# Django admin
class ModelAdmin:
    list_display = []  # Django admin config
    list_filter = []  # Django admin config
    search_fields = []  # Django admin config
    ordering = []  # Django admin config

# Django forms
class Form:
    def clean(self):  # Form validation
        pass
    
    def clean_field_name(self):  # Field validation
        pass

# Django serializers (DRF)
class Serializer:
    def validate(self, attrs):  # Serializer validation
        pass
    
    def validate_field_name(self, value):  # Field validation
        pass
    
    def create(self, validated_data):  # Create instance
        pass
    
    def update(self, instance, validated_data):  # Update instance
        pass

# ============================================================================
# SQLALCHEMY PATTERNS
# ============================================================================

# SQLAlchemy declarative base
class Model:
    __tablename__ = 'table'  # SQLAlchemy table name
    __table_args__ = {}  # SQLAlchemy table args
    
    id = None  # Common primary key
    created_at = None  # Common timestamp
    updated_at = None  # Common timestamp

# ============================================================================
# CELERY PATTERNS
# ============================================================================

@celery.task  # Celery task decorator
def celery_task():
    pass

@shared_task  # Celery shared task
def shared_celery_task():
    pass

# ============================================================================
# DATACLASS PATTERNS
# ============================================================================

from dataclasses import dataclass, field

@dataclass
class DataClass:
    # These often look unused but are used by dataclass
    field1: str = field(default="")
    field2: int = field(default=0)
    _private: str = field(default="", repr=False)

# ============================================================================
# PYDANTIC PATTERNS
# ============================================================================

from pydantic import BaseModel, Field, validator

class PydanticModel(BaseModel):
    # Pydantic model fields
    field1: str = Field(...)
    field2: int = Field(default=0)
    
    # Pydantic validators
    @validator('field1')
    def validate_field1(cls, v):
        return v
    
    class Config:  # Pydantic config
        arbitrary_types_allowed = True
        use_enum_values = True

# ============================================================================
# ENUM PATTERNS
# ============================================================================

from enum import Enum, auto

class Status(Enum):
    # Enum values often look unused
    PENDING = auto()
    PROCESSING = auto()
    COMPLETE = auto()
    ERROR = auto()

# ============================================================================
# EXCEPTION PATTERNS
# ============================================================================

class CustomException(Exception):
    """Custom exceptions often look unused but are raised elsewhere."""
    pass

class ValidationError(Exception):
    pass

class NotFoundError(Exception):
    pass

class PermissionError(Exception):
    pass

# ============================================================================
# METACLASS PATTERNS
# ============================================================================

class MetaClass(type):
    def __new__(mcs, name, bases, namespace):
        return super().__new__(mcs, name, bases, namespace)
    
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================

import os

# Environment variables often look unused
DEBUG = os.getenv('DEBUG', False)
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')
API_KEY = os.getenv('API_KEY')

# ============================================================================
# CONSTANTS
# ============================================================================

# Constants that might be imported elsewhere
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BUFFER_SIZE = 1024
CHUNK_SIZE = 8192

# Status codes
OK = 200
CREATED = 201
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403
NOT_FOUND = 404
INTERNAL_SERVER_ERROR = 500

# ============================================================================
# IMPORT ALIASES
# ============================================================================

# Common import aliases that might look unused
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import torch

# ============================================================================
# REGISTER/FACTORY PATTERNS
# ============================================================================

# Registry pattern
REGISTRY = {}

def register(name):
    """Decorator to register functions/classes."""
    def decorator(func):
        REGISTRY[name] = func
        return func
    return decorator

@register('example')
def registered_function():
    pass

# Factory pattern
class Factory:
    @classmethod
    def create(cls, type_name):
        pass

# ============================================================================
# PLUGIN/EXTENSION PATTERNS
# ============================================================================

def setup(app):
    """Common plugin setup function."""
    pass

def initialize_plugin():
    """Plugin initialization."""
    pass

def register_plugin():
    """Plugin registration."""
    pass

# ============================================================================
# NOTEBOOK/REPL PATTERNS
# ============================================================================

# Jupyter/IPython specific
get_ipython  # IPython global
In  # IPython input history
Out  # IPython output history

# Display functions
display  # IPython display
HTML  # IPython HTML display
Image  # IPython Image display

# ============================================================================
# MULTIPROCESSING/THREADING PATTERNS
# ============================================================================

def worker():
    """Worker function for threading/multiprocessing."""
    pass

def task():
    """Task function for async operations."""
    pass

def job():
    """Job function for queues."""
    pass

# ============================================================================
# TEMPLATE PATTERNS
# ============================================================================

# Jinja2 filters and tests
def jinja_filter(value):
    """Custom Jinja2 filter."""
    return value

def jinja_test(value):
    """Custom Jinja2 test."""
    return True

# ============================================================================
# SPHINX DOCUMENTATION PATTERNS
# ============================================================================

# Sphinx configuration
project = 'Project'
copyright = 'Copyright'
author = 'Author'
version = '1.0'
release = '1.0.0'
extensions = []
templates_path = []
exclude_patterns = []
html_theme = 'default'
html_static_path = []
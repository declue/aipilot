Installation
============

Requirements
------------

* Python 3.11 or higher
* PySide6 (Qt for Python)
* Additional dependencies listed in pyproject.toml

Installation Steps
------------------

1. Clone the repository:

.. code-block:: bash

   git clone https://github.com/yourusername/dspilot.git
   cd dspilot

2. Install dependencies:

.. code-block:: bash

   pip install -e ".[test]"

3. Run the application:

.. code-block:: bash

   python app.py

Development Installation
------------------------

For development, install additional dependencies:

.. code-block:: bash

   pip install -e ".[dev]"
   pre-commit install

Docker Installation
-------------------

Build and run with Docker:

.. code-block:: bash

   docker build -t dspilot .
   docker run -p 8000:8000 dspilot 
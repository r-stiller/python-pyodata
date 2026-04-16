# Python OData Client - pyodata

Python OData client which provides comfortable Python agnostic
way for communication with OData services.

The goal of this Python module is to hide all OData protocol implementation
details.

## Fork Notice

This repository is a fork of the original
[`SAP/python-pyodata`](https://github.com/SAP/python-pyodata) project and
continues to distribute the code under the Apache License, Version 2.0.

The current fork repository is
[`r-stiller/python-pyodata`](https://github.com/r-stiller/python-pyodata).

The original upstream attribution and notice are retained in [LICENSE](LICENSE)
and [NOTICE](NOTICE). This fork contains additional modifications relative to
upstream.

The fork-specific changes in this repository were vibecoded and have not been
checked by a human. Treat all fork-specific behavior as unreviewed until you
verify it yourself.

There is no warranty whatsoever for this fork. It is provided strictly on an
"AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or
implied, including MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, and
NON-INFRINGEMENT.

## Supported features

- OData V2
- OData V3, when selected explicitly via `odata_version=3`, for the current first
  milestone feature set

## Requirements

- [Python >= 3.9](https://www.python.org/downloads/)

## Download and Installation

Install and update using pip:

```bash
python -m pip install -U "git+https://github.com/r-stiller/python-pyodata.git"
```

## Configuration

You can start building your OData projects straight away after installing the
Python module without any additional configuration steps needed.

## Limitations

- OData V3 support must be selected explicitly with `odata_version=3`.
- OData V3 currently supports Verbose JSON only.
- The current V3 milestone covers client bootstrap, metadata parsing, entity
  querying and CRUD, function and action invocation, batch for the supported
  JSON request and response shapes, named and default stream reads, open types,
  and the tested `requests`, `httpx`, and `aiohttp` integrations.
- OData V3 does not yet provide JSON Light or Atom support, broad stream upload
  and write support, or general spatial URL literal and operation-parameter
  support.

## Known Issues

There are no known issues at this time.

## How to obtain support

For this fork, use the fork's own issue tracker and release process at
[`r-stiller/python-pyodata`](https://github.com/r-stiller/python-pyodata/issues).
Upstream support and issue triage belong to the original
[`SAP/python-pyodata`](https://github.com/SAP/python-pyodata) project.

## Usage

The only thing you need to do is to import the _pyodata_ Python module and
provide an object implementing interface compatible with [Session Object](https://2.python-requests.org/en/master/user/advanced/#session-objects)
for the library [Requests](https://2.python-requests.org/en/master/).

```python
import requests
import pyodata

SERVICE_URL = 'http://services.odata.org/V2/Northwind/Northwind.svc/'

# Create instance of OData client
client = pyodata.Client(SERVICE_URL, requests.Session())

# Select the current OData V3 implementation explicitly
client_v3 = pyodata.Client(
    'http://services.odata.org/V3/OData/OData.svc/',
    requests.Session(),
    odata_version=pyodata.Client.ODATA_VERSION_3)
```

Find more sophisticated examples in [The User Guide](docs/usage/README.md).

## Contributing

Please, go through [the Contributing guideline](CONTRIBUTING.md).

### Authoring a patch

Here's an example workflow for a project `PyOData` hosted on Github
Your username is `yourname` and you're submitting a basic bugfix or feature.

* Hit 'fork' on Github, creating e.g. `yourname/PyOData`.
* `git clone git@github.com:yourname/PyOData`
* `git checkout -b foo_the_bars` to create new local branch named foo_the_bars
* Hack, hack, hack
* Run `python3 -m pytest` or `make check`
* `git status`
* `git add`
* `git commit -s -m "Foo the bars"`
* `git push -u origin HEAD` to create foo_the_bars branch in your fork
* Visit your fork at Github and click handy "Pull request" button.
* In the description field, write down issue number (if submitting code fixing
  an existing issue) or describe the issue + your fix (if submitting a wholly
  new bugfix).
* Hit 'submit'! And please be patient - the maintainers will get to you when
  they can.

## License

This fork is distributed under the Apache License, Version 2.0.

Upstream attribution from the original SAP project is preserved in
[NOTICE](NOTICE) and [LICENSE](LICENSE). Additional fork notices are also
recorded in [NOTICE](NOTICE).

No warranty whatsoever is provided for this fork. See Section 7 of the Apache
License in [LICENSE](LICENSE).

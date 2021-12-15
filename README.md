ci-core-dumper
==============

A utility to automate analysis of core dumps from crashes during CI builds and test runs.

Support Linux (Github Actions, Travis-CI) and Windows (Appveyor, Github Actions, Travis-CI).

Usage on Github Actions:

```yaml
...
jobs:
  test:
    runs-on: ${{ matrix.os }}
    name: My Job
    steps:
      - uses: actions/checkout@v2
      - uses: mdavidsaver/ci-core-dumper@master
      - runs: |
         ulimit -c unlimited
         ... something which might crash
```

With Github Actions only, a dummy 'ulimit' command is provided on Windows.

Usage in Travis-CI:

```yaml
install:
  - sudo pip install git+https://github.com/mdavidsaver/ci-core-dumper#egg=ci-core-dumper

before_script:
  - sudo python -m ci_core_dumper install

script:
  - ulimit -c unlimited
  - ... something which might crash

after_failure:
  - python -m ci_core_dumper report
```

Info on [stages](https://docs.travis-ci.com/user/job-lifecycle/#the-job-lifecycle).

Usage in Appveyor:

```yaml
install:
  - cmd: pip install git+https://github.com/mdavidsaver/ci-core-dumper#egg=ci-core-dumper

before_test:
  - cmd: python -m ci_core_dumper install

test_script:
  - ... something which might crash

on_failure:
  - cmd: python -m ci_core_dumper report
```

Info on [stages](https://www.appveyor.com/docs/build-configuration/#build-pipeline).

User setup verification
-----------------------

Test crashes should be rare.
So the best case is that ci-core-dumper is installed but never used.
There is a risk of false negatives if some issue prevents ci-core-dumper from functioning correctly.
eg. omitting 'ulimit -c unlimited' on *NIX or SetErrorMode(2) on Windows.

Extra Commands
--------------

The action arguments `extra_cdb:` and `extra_gdb:` can be used to pass
a semicolon separated list of extra debugger commands to CDB or GDB.  eg.

```yaml
...
jobs:
...
      - uses: mdavidsaver/ci-core-dumper@master
        with:
          extra_gdb: "info auto-load"
```


Development
-----------

Please report any issue on the Github project.

* [Github Project](https://github.com/mdavidsaver/ci-core-dumper)
* [Travis-CI status](https://travis-ci.org/github/mdavidsaver/ci-core-dumper)
* [Appveyor status](https://ci.appveyor.com/project/mdavidsaver/ci-core-dumper)

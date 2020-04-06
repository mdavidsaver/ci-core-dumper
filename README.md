ci-core-dumper
==============

A utility to automate analysis of core dumps from crashes during CI builds and test runs.

Support Linux (Travis-CI) and Windows (Appveyor).

Usage in Travis-CI:

```yaml
install:
  - sudo pip install git+https://github.com/mdavidsaver/ci-core-dumper#egg=ci-core-dumper

before_script:
  - sudo ci-core-dumper install

script:
  - ... something which might crash

after_failure:
  - ci-core-dumper report
```

Info on [stages](https://docs.travis-ci.com/user/job-lifecycle/#the-job-lifecycle).

Usage in Appveyor:

```yaml
install:
  - cmd: pip install git+https://github.com/mdavidsaver/ci-core-dumper#egg=ci-core-dumper

before_test:
  - cmd: ci-core-dumper install

test_script:
  - ... something which might crash

on_failure:
  - cmd: ci-core-dumper report
```

Info on [stages](https://www.appveyor.com/docs/build-configuration/#build-pipeline).

Development
-----------

Please report any issue on the Github project.

* [Github Project](https://github.com/mdavidsaver/ci-core-dumper)
* [Travis-CI status](https://travis-ci.org/github/mdavidsaver/ci-core-dumper)
* [Appveyor status](https://ci.appveyor.com/project/mdavidsaver/ci-core-dumper)

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
  - ulimit -c unlimited
  - ci-core-dumper crash --direct # remove after verification
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
  - cmd: ci-core-dumper crash --direct # remove after verification
  - ... something which might crash

on_failure:
  - cmd: ci-core-dumper report
```

Info on [stages](https://www.appveyor.com/docs/build-configuration/#build-pipeline).

User setup verification
-----------------------

Test crashes should be rare.
So the best case is that ci-core-dumper is install but never used.
There is a risk of false negatives if some issue prevents ci-core-dumper from functioning correctly.
eg. omitting 'ulimit -c unlimited'.

When first setting up a new build to use ci-core-dumper it is highly recommended
to initially include "ci-core-dumper crash --direct" as shown above.
This should produce a core, cause the CI build to fail,
and result in a report.

An option for later testing is to include "ci-core-dumper crash"
which will produce a core file from a sub-process and then return 0.
This will not fail the build by itself.
However, if the build fails for other reasons, the report should show
at least this one crash.

Development
-----------

Please report any issue on the Github project.

* [Github Project](https://github.com/mdavidsaver/ci-core-dumper)
* [Travis-CI status](https://travis-ci.org/github/mdavidsaver/ci-core-dumper)
* [Appveyor status](https://ci.appveyor.com/project/mdavidsaver/ci-core-dumper)

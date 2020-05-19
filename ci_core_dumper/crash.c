
#include <Python.h>

static PyObject* doCrash(PyObject* unused)
{
    *(char*)0 = 0;
    return PyErr_Format(PyExc_RuntimeError, "oops.  failed to crash");
}

static struct PyMethodDef crash_methods[] = {
    {"crash", (PyCFunction)&doCrash, METH_NOARGS, "SIGSEGV"},
    {NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef crashmodule = {
  PyModuleDef_HEAD_INIT,
    "ci_core_dumper._crash",
    NULL,
    -1,
    crash_methods,
};
#endif

#if PY_MAJOR_VERSION >= 3
#  define PyMOD(NAME) PyObject* PyInit_##NAME (void)
#else
#  define PyMOD(NAME) void init##NAME (void)
#endif

PyMOD(_crash)
{
#if PY_MAJOR_VERSION >= 3
        PyObject *mod = PyModule_Create(&crashmodule);
#else
        PyObject *mod = Py_InitModule("ci_core_dumper._crash", crash_methods);
#endif
        if(mod) {
        }
#if PY_MAJOR_VERSION >= 3
    return mod;
#else
    (void)mod;
#endif
}

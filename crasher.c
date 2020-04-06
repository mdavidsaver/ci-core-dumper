
#ifdef _WIN32
#  include <windows.h>
#  include <crtdbg.h>
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

volatile int* volatile oops;

void doAbort()
{
    abort();
}

int doCrash()
{
    return *oops;
}

int main(int argc, char *argv[])
{
#ifdef _WIN32
    /* disable abort() dialog */
    _CrtSetReportMode( _CRT_ASSERT, _CRTDBG_MODE_FILE |_CRTDBG_MODE_DEBUG );
    _CrtSetReportFile( _CRT_ASSERT, _CRTDBG_FILE_STDERR );
    _CrtSetReportMode( _CRT_ERROR, _CRTDBG_MODE_FILE |_CRTDBG_MODE_DEBUG );
    _CrtSetReportFile( _CRT_ERROR, _CRTDBG_FILE_STDERR );
    _CrtSetReportMode( _CRT_WARN, _CRTDBG_MODE_FILE |_CRTDBG_MODE_DEBUG );
    _CrtSetReportFile( _CRT_WARN, _CRTDBG_FILE_STDERR );
#endif

    if(argc<2) {
        printf("%s [abort|crash]\n", argv[0]);
        return 2;
    } else if(strcmp(argv[1], "abort")==0) {
        doAbort();
        return 0; // not going to happen
    } else if(strcmp(argv[1], "crash")==0) {
        return doCrash();
    } else {
        return 3;
    }
}

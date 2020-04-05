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

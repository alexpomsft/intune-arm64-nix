#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char** argv)
{
    const char* name = strrchr(argv[0], '/');
    name = name ? name + 1 : argv[0];
    const char* program;
    const char* mode;
    if(!strcmp(name, "WebKitWebProcess")) {
        program = "/usr/lib/intune-arm64/WebKitWebProcess";
        mode = "1";
    } else if(!strcmp(name, "WebKitNetworkProcess")) {
        program = "/usr/lib/intune-arm64/WebKitNetworkProcess";
        mode = "0";
    } else {
        fprintf(stderr, "Unexpected WebKit helper: %s\n", name);
        return 2;
    }
    if(setenv("BOX64_DYNAREC", mode, 1)) {
        perror("Set WebKit process execution mode");
        return 1;
    }
    char** arguments = calloc((size_t)argc + 2, sizeof(*arguments));
    if(!arguments) {
        perror("Allocate WebKit helper arguments");
        return 1;
    }
    arguments[0] = "/usr/lib/intune-arm64/box64";
    arguments[1] = (char*)program;
    for(int i = 1; i < argc; ++i)
        arguments[i + 1] = argv[i];
    execv(arguments[0], arguments);
    perror("Execute translated WebKit helper");
    free(arguments);
    return 127;
}

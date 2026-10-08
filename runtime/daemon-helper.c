#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void)
{
    const char* count = getenv("LISTEN_FDS");
    struct stat descriptor;
    if(!count || strcmp(count, "1") || fstat(3, &descriptor) || !S_ISSOCK(descriptor.st_mode)) {
        fprintf(stderr, "Expected exactly one inherited systemd listening socket\n");
        return 1;
    }
    char pid[32];
    snprintf(pid, sizeof(pid), "%ld", (long)getpid());
    // Bubblewrap forks; socket activation must identify the final payload PID.
    if(setenv("LISTEN_PID", pid, 1)) {
        perror("Set socket activation PID");
        return 1;
    }
    char* const arguments[] = {
        "/usr/lib/intune-arm64/box64",
        "/opt/microsoft/intune/bin/intune-daemon",
        NULL,
    };
    execv(arguments[0], arguments);
    perror("Execute translated Intune daemon");
    return 127;
}

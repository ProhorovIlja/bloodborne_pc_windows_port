/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_crt_init_plan_v409.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL at %d\n",__LINE__); abort(); } } while (0)
typedef struct {
    char log[128];
    size_t n;
    int fail_env, fail_init, fill;
    ShytCrtV409 *crt;
    const ShytCrtHooksV409 *hooks;
} Test;
static void mark(Test *t, char c) { CHECK(t->n < sizeof(t->log)-1); t->log[t->n++] = c; }
static void loader(void *v) {
    Test *t=v;
    CHECK(!shyt_crt_register_v409(t->crt,(ShytExitEntryV409){loader,v}));
    mark(t,'L');
}
static void image(void *v) { mark(v,'D'); }
static void extra(void *v) { mark(v,'X'); }
static int environment(void *v,int argc,char *const *argv,char *const *envp) {
    Test *t=v;
    CHECK(argc==1 && !strcmp(argv[0],"test") && !strcmp(envp[0],"A=B"));
    CHECK(t->crt->phase==SHYT_CRT_ENV_V409);
    mark(t,'E');
    return !t->fail_env;
}
static int initializers(void *v,ShytCrtV409 *crt) {
    Test *t=v;
    CHECK(t->crt==crt && crt->phase==SHYT_CRT_INIT_V409);
    CHECK(!shyt_crt_register_v409(crt,(ShytExitEntryV409){0}));
    mark(t,'I');
    CHECK(shyt_crt_register_v409(crt,(ShytExitEntryV409){extra,v}));
    return !t->fail_init;
}
static int game_main(void *v,ShytCrtV409 *crt,int argc,char *const *argv,void *third) {
    Test *t=v;
    int sentinel=11;
    CHECK(t->crt==crt && crt->phase==SHYT_CRT_MAIN_V409);
    CHECK(argc==1 && !strcmp(argv[0],"test") && !third);
    CHECK(!shyt_crt_run_v409(crt,t->hooks,t,argc,argv,NULL,&sentinel) && sentinel==11);
    if(t->fill) {
        for (size_t i=crt->count;i<SHYT_CRT_MAX_EXIT_V409;++i)
            CHECK(shyt_crt_register_v409(crt,(ShytExitEntryV409){extra,v}));
        CHECK(!shyt_crt_register_v409(crt,(ShytExitEntryV409){extra,v}));
    }
    mark(t,'M');
    return -123;
}
static void returned(void *v,int status) {
    Test *t=v;
    CHECK(status==-123 && t->crt->phase==SHYT_CRT_NOTIFY_V409);
    mark(t,'R');
}
static int first(void *v,ShytCrtV409 *crt) {
    CHECK(crt->phase==SHYT_CRT_INIT_V409);
    mark(v,'1');
    return 1;
}
static int second(void *v,ShytCrtV409 *crt) {
    CHECK(crt->phase==SHYT_CRT_INIT_V409);
    mark(v,'2');
    return 1;
}
static void plans(void) {
    ShytCrtV409 crt={0};
    Test t={0};
    const ShytInitBindingV409 b[]={{10,first},{20,second}};
    const ShytInitBindingV409 bad[]={{10,first},{10,second}};
    const uint64_t f[]={10,20}, l[]={10,20}, unknown[]={10,99};
    CHECK(!shyt_init_run_v409(&crt,&t,b,2,f,2,l,2));
    crt.phase=SHYT_CRT_INIT_V409;
    CHECK(!shyt_init_run_v409(&crt,&t,b,2,f,2,unknown,2));
    CHECK(!shyt_init_run_v409(&crt,&t,bad,2,f,2,l,2));
    CHECK(t.n==0);
    CHECK(shyt_init_run_v409(&crt,&t,b,2,f,2,l,2));
    CHECK(!strcmp(t.log,"1221"));
}
int main(void) {
    plans();
    char arg[]="test", env[]="A=B";
    char *argv[]={arg,NULL}, *envp[]={env,NULL};
    for (int mode=0; mode<5; ++mode) {
        ShytCrtV409 crt={0};
        Test t={0};
        const ShytCrtHooksV409 hooks={
            environment,{loader,&t},{image,&t},initializers,game_main,returned
        };
        int status=99;
        t.crt=&crt;t.hooks=&hooks;t.fail_env=mode==1;t.fail_init=mode==2;t.fill=mode==3;
        if (mode==4) {
            char *invalid[]={NULL,NULL};
            CHECK(!shyt_crt_run_v409(&crt,&hooks,&t,1,invalid,envp,&status));
            CHECK(crt.phase==SHYT_CRT_NEW_V409 && status==99 && t.n==0);
            continue;
        }
        const int ok=shyt_crt_run_v409(&crt,&hooks,&t,1,argv,envp,&status);
        CHECK(crt.count==0);
        CHECK(!shyt_crt_run_v409(&crt,&hooks,&t,1,argv,envp,&status));
        if (mode==1 || mode==2) {
            CHECK(!ok && status==99 && crt.phase==SHYT_CRT_FAILED_V409);
            CHECK(!strcmp(t.log,mode==1?"E":"EIXDL"));
        } else {
            CHECK(ok && status==-123 && crt.phase==SHYT_CRT_DONE_V409);
            if (mode==0) CHECK(!strcmp(t.log,"EIMRXDL"));
            else {
                CHECK(t.n==4+SHYT_CRT_MAX_EXIT_V409 && !memcmp(t.log,"EIMR",4));
                for(size_t i=4;i<t.n-2;++i) CHECK(t.log[i]=='X');
                CHECK(!strcmp(t.log+t.n-2,"DL"));
            }
        }
    }
    puts("NATIVE_V409_CRT_LIFECYCLE_PASS");
    return 0;
}

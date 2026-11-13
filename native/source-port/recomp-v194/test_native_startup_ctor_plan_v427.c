/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_startup_ctor_plan_v427.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V427_FAIL %d\n",__LINE__);abort();} }while(0)
static void a(BbCpu *c){c->r[0]=c->r[0]*10u+1u;}
static void b(BbCpu *c){c->r[0]=c->r[0]*10u+2u;}
int main(void) {
    RcFunction registry[]={{.offset=10,.fn=a},{.offset=20,.fn=b}};
    ShytCtorRowV427 rows[]={{93,20},{94,10},{95,20}};
    RcFn out[]={NULL,NULL,NULL};
    rows[2].id=30;
    CHECK(!shyt_ctor_prepare_v427(rows,3,93,registry,2,out,3));
    CHECK(!out[0] && !out[1] && !out[2]);
    rows[2].id=20; rows[1].ordinal=95;
    CHECK(!shyt_ctor_prepare_v427(rows,3,93,registry,2,out,3));
    rows[1].ordinal=94;
    CHECK(!shyt_ctor_prepare_v427(rows,3,93,registry,2,out,2));
    registry[1].fn=NULL;
    CHECK(!shyt_ctor_prepare_v427(rows,3,93,registry,2,out,3));
    registry[1].fn=b; registry[1].offset=10;
    CHECK(!shyt_ctor_prepare_v427(rows,3,93,registry,2,out,3));
    registry[1].offset=20;
    CHECK(!out[0] && !out[1] && !out[2]);
    CHECK(shyt_ctor_prepare_v427(rows,3,93,registry,2,out,3));
    BbCpu cpu={0};
    for(size_t i=0;i<3;++i)out[i](&cpu);
    CHECK(cpu.r[0]==212);
    puts("NATIVE_V427_CTOR_PLAN_PASS");
    return 0;
}

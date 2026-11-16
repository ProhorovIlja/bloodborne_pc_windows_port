/* SPDX-License-Identifier: GPL-2.0-or-later */
enum { DATA_SIZE=512 };
static const uint64_t data_base=4096, stack_base=8192;
static const struct bb_patch_v474 patches[]={
    {0,4352},{64,55},{72,77},{128,4480},{272,500},{280,600},{416,700}
};
static const uint64_t fields[]={55,77};
static const struct startup_getter_v465 getters[]={{1,4096,4352,500,0},{2,4096,4352,600,1}};
static const struct startup_route_v464 sret={{3,4},4224,4480,700,0x73};

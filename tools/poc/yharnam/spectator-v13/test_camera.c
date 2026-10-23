#ifdef NDEBUG
#undef NDEBUG
#endif
#define _GNU_SOURCE
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static volatile uint64_t fake_delta;
static volatile uint64_t *delta=&fake_delta;
enum {CAM_PITCH=0x140,CAM_YAW=0x144,CAM_PIVOT=0xd0,CAM_DRAWN=0x100};
static float *field(unsigned char *camera,unsigned offset){return (float *)(camera+offset);}
void runtime_camhook_turn(float pitch,float yaw){(void)pitch;fake_delta+=yaw>0?1:0;}
#include "spectator_camera.inc"
int main(void){
  unsigned char camera[0x400]={0};
  float *pivot=field(camera,CAM_PIVOT),*drawn=field(camera,CAM_DRAWN);
  pivot[0]=3;pivot[1]=2;pivot[2]=1;
  drawn[0]=3;drawn[1]=3;drawn[2]=-1;
  runtime_camhook_spectator(1,10,0,10,0,0,0);
  assert(fake_delta);sh_spectator_frame(camera);
  assert(pivot[0]>3&&pivot[0]<10);
  assert(fabsf(drawn[0]-pivot[0])<0.00001f);
  const float old=pivot[0];
  runtime_camhook_spectator(2,0,0,0,0.1f,0.1f,0.1f);
  sh_spectator_frame(camera);
  assert(pivot[0]>old);
  runtime_camhook_spectator(0,0,0,0,0,0,0);
  sh_spectator_frame(camera);assert(sh_last_mode==0);
  runtime_camhook_spectator(99,0,0,0,0,0,0);
  sh_spectator_frame(camera);assert(sh_last_mode==0);
  puts("PASS V13 native camera: follow/free, disable on respawn");
}

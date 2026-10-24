/* Seamless Hunt V13: camera-only native 1.09 spectator. Requires existing hook.
 * No character, collision, save, or world authority writes.
 */
typedef struct {
    unsigned int version;
    int mode; /* 0 game, 1 follow, 2 free */
    uint32_t data[6]; /* target xyz and frame motion xyz */
} ShSpectatorWire;
static ShSpectatorWire sh_spectator;
static float sh_free_center[3],sh_follow_center[3];
static int sh_last_mode;
static unsigned char *sh_last_camera;
static unsigned int sh_freesteps;
static uint32_t sh_bits(float x){uint32_t raw;memcpy(&raw,&x,sizeof(raw));return raw;}
static float sh_float(uint32_t raw){float x;memcpy(&x,&raw,sizeof(x));return x;}
void runtime_camhook_spectator(int mode,float x,float y,float z,
                               float strafe,float rise,float forward){
    if(mode<0||mode>2||!delta)mode=0;
    __atomic_add_fetch(&sh_spectator.version,1,__ATOMIC_ACQ_REL);
    const float state[6]={x,y,z,strafe,rise,forward};
    for(int i=0;i<6;++i)__atomic_store_n(&sh_spectator.data[i],sh_bits(state[i]),__ATOMIC_RELAXED);
    __atomic_store_n(&sh_spectator.mode,mode,__ATOMIC_RELAXED);
    __atomic_add_fetch(&sh_spectator.version,1,__ATOMIC_RELEASE);
    /* Existing x64 camera stub calls its callback when mouse delta is nonzero. */
    if(mode)runtime_camhook_turn(0,0.00000001f);
}
static void sh_spectator_frame(unsigned char *camera){
    const unsigned int before=__atomic_load_n(&sh_spectator.version,__ATOMIC_ACQUIRE);
    if(before&1)return;
    float read[6];
    for(int i=0;i<6;++i)read[i]=sh_float(__atomic_load_n(&sh_spectator.data[i],__ATOMIC_RELAXED));
    const int mode=__atomic_load_n(&sh_spectator.mode,__ATOMIC_RELAXED);
    if(before!=__atomic_load_n(&sh_spectator.version,__ATOMIC_ACQUIRE))return;
    if(mode==0){sh_last_mode=0;sh_last_camera=NULL;return;}
    for(int i=0;i<6;++i)if(!isfinite(read[i]))return;
    float *pivot=field(camera,CAM_PIVOT),*drawn=field(camera,CAM_DRAWN);
    for(int i=0;i<3;++i)if(!isfinite(pivot[i])||!isfinite(drawn[i]))return;
    if(mode!=sh_last_mode||camera!=sh_last_camera){
        for(int i=0;i<3;++i){sh_follow_center[i]=pivot[i];sh_free_center[i]=pivot[i];}
        sh_freesteps=0;sh_last_mode=mode;sh_last_camera=camera;
    }
    float destination[3];
    if(mode==1){
        for(int i=0;i<3;++i){
            const float target=read[i]+(i==1?1.35f:0);
            if(fabsf(target)>100000.0f)return;
            sh_follow_center[i]+=(target-sh_follow_center[i])*0.18f;
            destination[i]=sh_follow_center[i];
        }
    }else{
        /* Deliberately camera-local and bounded to the loaded world. */
        const float yaw=*field(camera,CAM_YAW);
        if(!isfinite(yaw))return;
        const float side=fmaxf(-0.35f,fminf(0.35f,read[3]));
        const float rise=fmaxf(-0.35f,fminf(0.35f,read[4]));
        const float ahead=fmaxf(-0.35f,fminf(0.35f,read[5]));
        const float move[3]={cosf(yaw)*side+sinf(yaw)*ahead,rise,
                              -sinf(yaw)*side+cosf(yaw)*ahead};
        if(sh_freesteps++<36000)for(int i=0;i<3;++i)sh_free_center[i]+=move[i];
        for(int i=0;i<3;++i){
            const float relative=sh_free_center[i]-pivot[i];
            if(relative>45.0f)sh_free_center[i]=pivot[i]+45.0f;
            if(relative< -45.0f)sh_free_center[i]=pivot[i]-45.0f;
            destination[i]=sh_free_center[i];
        }
    }
    /* Camera pivot and drawn position move together, avoiding spring lag. */
    for(int i=0;i<3;++i){
        const float offset=destination[i]-pivot[i];
        pivot[i]+=offset;drawn[i]+=offset;
    }
}

import { useState , useEffect } from "react";
import { delay, easeInOut, motion, setTarget, useAnimationFrame, useMotionValue, useSpring, useTransform } from "framer-motion";
import { clipPath } from "framer-motion/client";


function useConfiguredPulse(baseProgress, { duration, delay = 0, keyframes, masterCycle = 2.8 }) {
  

  // Tính tỷ lệ mốc thời gian trên thang đo 0 -> 1

  // Chia nhỏ khoảng thời gian active cho 4 mốc scale
  const t0 = 0;
  const t1 = delay / masterCycle; // Hết delay
  const t2 = t1 + (duration * 0.33) / masterCycle;
  const t3 = t1 + (duration * 0.66) / masterCycle;
  const t4 = (delay + duration) / masterCycle; // Hết duration
  const t5 = 1;

  // Output tương ứng: trước delay và sau repeatDelay luôn đứng yên ở scale = 1
  const outputScale = [
    keyframes[0],       // 0 -> startRatio: đứng yên (delay)
    keyframes[0],       // Bắt đầu nhịp
    keyframes[1],       // Đỉnh 1
    keyframes[2],       // Đỉnh 2 (co lại)
    keyframes[3],       // Kết thúc co giãn
    keyframes[3]        // endRatio -> 1: đứng yên (repeatDelay)
  ];

  return useTransform(
    baseProgress,
    [t0, t1, t2, t3, t4, t5],
    outputScale,
    { ease: easeInOut }
  );
}

function FairyUI({MasterCycle, RotateSpeed = 60, RotateReverse = false, PulseSpeed = 1, PulseDuration = 1.5, PulseDelay = 0.3, 
         PulseKeyFrameValue = [1, 0.85, 1.15, 1]
})
{

    if(!MasterCycle)
    {
        MasterCycle = PulseDuration + PulseDelay + PulseRepeatDelay + 0.3;
    }

    const speed = useSpring(RotateSpeed, {damping:20, stiffness: 100});
    const pulseFreq = useSpring(PulseSpeed, {damping:20, stiffness:100});

    const rotate = useMotionValue(0);
    const pulsePhase = useMotionValue(0);



    useEffect(()=>
    {
        speed.set(RotateSpeed);
    }, [RotateSpeed, speed]);

    useEffect(()=>{
        pulseFreq.set(PulseSpeed)
    }, [PulseSpeed, pulseFreq]);



    useAnimationFrame((_, delta) =>
    {
        const milidelta = delta/1000;
        const currentSpeed = speed.get();
        if(RotateReverse)
        {
            rotate.set(rotate.get() - milidelta * currentSpeed);
        }
        else
        {
            rotate.set(rotate.get() + milidelta * currentSpeed);
        }
        
        pulsePhase.set((pulsePhase.get() + (milidelta * pulseFreq.get()) /  MasterCycle) %1) ;
    });



    const scaleLayerWhite = useConfiguredPulse(pulsePhase,
       { 
        duration: PulseDuration,
        delay: PulseDelay + 0.3,
        keyframes: PulseKeyFrameValue,
        masterCycle : MasterCycle
        }
    );
    
    const scaleIrisOne = useConfiguredPulse(pulsePhase,
       { 
        duration: PulseDuration,
        delay: PulseDelay + 0.2,
        keyframes: PulseKeyFrameValue,
        masterCycle : MasterCycle
        }
    );

    const scaleIrisTwo = useConfiguredPulse(pulsePhase,
       { 
        duration: PulseDuration,
        delay: PulseDelay + 0.1,
        keyframes: PulseKeyFrameValue,
        masterCycle : MasterCycle
        }
    );

    const scaleIrisThree = useConfiguredPulse(pulsePhase,
       { 
        duration: PulseDuration,
        delay: PulseDelay + 0.2,
        keyframes: PulseKeyFrameValue,
        masterCycle : MasterCycle
        }
    );
    
    

    

    let scaleRatio = 1.18;
    const pulseTransition = (duration,delayTime, repeatDelay) => ({
    duration: duration,
    repeat: Infinity,
    ease: "easeInOut",
    delay: delayTime, 
    repeatDelay: repeatDelay
    });
    return(
    
        <main >          
            <div className="flex  h-[75vmin] w-[75vmin] items-center justify-center">
                <motion.div  
                className=" overflow-hidden absolute flex h-[60vmin] w-[60vmin] items-center rounded-full justify-center bg-blue-700 shadow-2xl ">
                
                <div className = "overflow-hidden flex items-center justify-center w-full h-full">   
                    <motion.div
                        style={{rotate}}
                        className="absolute flex h-[41vmin] w-[41vmin] rounded-xl aspect-square items-center justify-center bg-blue-950">
                        </motion.div>
                    
                        <div 
                            className="absolute flex h-[50vmin] aspect-square items-center rounded-full justify-center bg-blue-950">
                        </div>

                        <motion.div
                        style={{scale: scaleLayerWhite}}
                        className=" absolute flex h-[42vmin] aspect-square items-center rounded-full justify-center bg-white">
                        </motion.div>
                        
                        <motion.div
                            style={{scale: scaleIrisOne}}
                            className="absolute flex  h-[20vmin] aspect-square items-center rounded-full justify-center bg-gray-400">   
                        </motion.div>

                        <motion.div 
                            style={{scale: scaleIrisTwo}}
                            className="absolute flex  h-[15vmin] aspect-square items-center rounded-full justify-center bg-blue-700">
                        </motion.div >
                                
                        <motion.div
                            style={{scale: scaleIrisThree}}
                            className="absolute flex h-[10vmin] aspect-square items-center rounded-full justify-center bg-blue-950">
                        </motion.div> 

                    </div>
                    </motion.div>
                </div> 
        </main>
    );
};
export default FairyUI;
import { useState , useEffect } from "react";
import { motion, setTarget, useAnimationFrame, useMotionValue, useSpring } from "framer-motion";
import { clipPath } from "framer-motion/client";



function FairyUI({RotateSpeed})
{

    const speed = useSpring(RotateSpeed, {damping:20, stiffness: 100});
    const rotate = useMotionValue(0);


    useAnimationFrame((_, delta) =>
    {
        const currentSpeed = speed.get();
        rotate.set(rotate.get() + (delta/1000) * currentSpeed);
    });

    useEffect(()=>
    {
        speed.set(RotateSpeed);
    })



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
                animate={{ scale: [1, 1, 1] }}
                transition={pulseTransition(1.5,0,0)}
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
                        animate={{ scale: [1, 1.1, 0.9,1] }}
                        transition={pulseTransition(1.5,0.3,1)}
                        className=" absolute flex h-[42vmin] aspect-square items-center rounded-full justify-center bg-white">
                        </motion.div>
                        
                        <motion.div
                            animate={{ scale: [1, 1.3, 0.92, 1] }}
                            transition={pulseTransition(1.5,0.2,1)}
                            className="absolute flex  h-[20vmin] aspect-square items-center rounded-full justify-center bg-gray-400">   
                        </motion.div>

                        <motion.div 
                            animate={{ scale: [1, 1.2, 0.95, 1] }}
                            transition={pulseTransition(1.5,0.1,1)}
                            className="absolute flex  h-[15vmin] aspect-square items-center rounded-full justify-center bg-blue-700">
                        </motion.div >
                                
                        <motion.div
                            animate={{ scale: [1, 1.15, 0.98, 1] }}
                            transition={pulseTransition(1.5,0,1)}
                            className="absolute flex h-[10vmin] aspect-square items-center rounded-full justify-center bg-blue-950">
                        </motion.div> 

                    </div>
                    </motion.div>
                </div> 
        </main>
    );
};
export default FairyUI;
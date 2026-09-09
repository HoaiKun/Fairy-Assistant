import { useState } from "react";
import { motion } from "framer-motion";
import { clipPath } from "framer-motion/client";
function FairyUI()
{

    const glitchAnimation = {
        clipPath:[
        "inset(40% 0 61% 0)",
        "inset(92% 0 1% 0)",
        "inset(10% 0 75% 0)",
        "inset(0% 0 0% 0)",
        ],
        x : [-2,3-4,0],
        opacity:[0.8,1,0.9,1]
    }

    let scaleRatio = 1.18;
    const pulseTransition = (duration,delayTime, repeatDelay) => ({
    duration: duration,
    repeat: Infinity,
    ease: "easeInOut",
    delay: delayTime, 
    repeatDelay: repeatDelay
    });
    return(
    
        <main className="flex justify-center items-center">           
            <motion.div  
                animate={{ scale: [1, 1, 1] }}
                transition={pulseTransition(1.5,0,0)}
                className=" overflow-hidden absolute flex h-[60vmin] w-[60vmin] items-center rounded-full justify-center bg-blue-700 ">
                
                <div className = "overflow-hidden flex items-center justify-center w-full h-full">   
                    <motion.div
                    animate = {{rotate:360}}
                    transition={{
                        duration:4,
                        repeat:Infinity,
                        ease:"linear"
                    }}
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
                        className="absolute flex  h-[25vmin] aspect-square items-center rounded-full justify-center bg-gray-400">   
                    </motion.div>

                    <motion.div 
                        animate={{ scale: [1, 1.2, 0.95, 1] }}
                        transition={pulseTransition(1.5,0.1,1)}
                        className="absolute flex  h-[20vmin] aspect-square items-center rounded-full justify-center bg-blue-700">
                    </motion.div >
                            
                    <motion.div
                        animate={{ scale: [1, 1.15, 0.98, 1] }}
                        transition={pulseTransition(1.5,0,1)}
                        className="absolute flex h-[12vmin] aspect-square items-center rounded-full justify-center bg-blue-950">
                    </motion.div> 

                </div>

                

            </motion.div>

              

           
        </main>
    );
};
export default FairyUI;
import {defineConfig} from 'vite';
import {resolve} from 'node:path';
export default defineConfig({publicDir:resolve(import.meta.dirname,'../public'),build:{outDir:resolve(import.meta.dirname,'../dist'),emptyOutDir:true,rollupOptions:{input:{main:resolve(import.meta.dirname,'index.html'),waterCycleLab:resolve(import.meta.dirname,'water-cycle-lab.html'),lottieLab:resolve(import.meta.dirname,'lottie-lab.html')}}}});

import { AnimatePresence, motion } from 'motion/react';
import { useStore } from './lib/store';
import { BrandHeader } from './components/BrandHeader';
import { InputView } from './views/InputView';
import { ProcessingView } from './views/ProcessingView';
import { ResultView } from './views/ResultView';
import { ErrorView } from './views/ErrorView';

// Short, purposeful transitions. Reduced-motion is handled globally in CSS.
const variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

export function App() {
  const phase = useStore((s) => s.phase);

  return (
    <div className="app">
      <div className="app__inner">
        <BrandHeader />
        <AnimatePresence mode="wait" initial={false}>
          <motion.main
            key={phase}
            variants={variants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {phase === 'input' && <InputView />}
            {phase === 'processing' && <ProcessingView />}
            {phase === 'result' && <ResultView />}
            {phase === 'error' && <ErrorView />}
          </motion.main>
        </AnimatePresence>
      </div>
    </div>
  );
}

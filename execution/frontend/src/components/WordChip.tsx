import { motion } from 'motion/react';
import type { WordResult } from '../lib/types';
import { wordStatusLabel, wordStatusSymbol } from '../lib/format';

interface Props {
  word: WordResult;
  index: number;
}

// A single word/phrase chip. Status is conveyed by color, a symbol, and a text
// label so color is never the sole indicator (accessibility rule).
export function WordChip({ word, index }: Props) {
  const label = wordStatusLabel(word.status);
  return (
    <motion.span
      className={`chip chip--${word.status}`}
      initial={{ opacity: 0, y: 6, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: Math.min(index * 0.035, 0.4), duration: 0.22 }}
      title={`${word.source_text} — ${label}`}
    >
      <span className="chip__symbol" aria-hidden="true">
        {wordStatusSymbol(word.status)}
      </span>
      <span className="chip__text">{word.source_text}</span>
      {word.russian_gloss && (
        <span className="chip__gloss">{word.russian_gloss}</span>
      )}
      <span className="chip__status">{label}</span>
    </motion.span>
  );
}

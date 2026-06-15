// Demo phrases chosen for high dictionary coverage (see source.md vocabulary).
// These insert predictably into the input; they replace the current text.

export interface DemoPhrase {
  text: string;
  hint: string;
}

export const demoPhrases: DemoPhrase[] = [
  { text: 'salom', hint: 'Salomlashish' },
  { text: 'katta rahmat', hint: 'Birikma' },
  { text: 'bugun yaxshi kun', hint: 'Kundalik' },
  { text: 'bir ikki uch', hint: 'Sonlar' },
  { text: 'men kitob o‘qiyman', hint: 'Qo‘shimchali' },
];

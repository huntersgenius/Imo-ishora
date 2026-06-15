import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import { formatDuration } from '../lib/format';

type PlayerState = 'loading' | 'ready' | 'playing' | 'paused' | 'ended' | 'error';

interface Props {
  src: string;
}

// Custom HTML5 player with branded chrome. Stable 9:16 stage so the layout
// never jumps. Full keyboard support and accessible control labels.
export function VideoPlayer({ src }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [state, setState] = useState<PlayerState>('loading');
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loop, setLoop] = useState(false);

  // Reset when the source changes (new synthesis).
  useEffect(() => {
    setState('loading');
    setCurrent(0);
    setDuration(0);
  }, [src]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused || v.ended) {
      void v.play();
    } else {
      v.pause();
    }
  }, []);

  const replay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = 0;
    void v.play();
  }, []);

  const seek = useCallback((value: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = value;
    setCurrent(value);
  }, []);

  const toggleFullscreen = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else if (v.requestFullscreen) {
      void v.requestFullscreen();
    }
  }, []);

  const onKeyDown = useCallback(
    (e: ReactKeyboardEvent) => {
      const v = videoRef.current;
      if (!v) return;
      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault();
          togglePlay();
          break;
        case 'ArrowRight':
          e.preventDefault();
          seek(Math.min(v.duration || 0, v.currentTime + 5));
          break;
        case 'ArrowLeft':
          e.preventDefault();
          seek(Math.max(0, v.currentTime - 5));
          break;
        case 'f':
          e.preventDefault();
          toggleFullscreen();
          break;
        default:
          break;
      }
    },
    [seek, togglePlay, toggleFullscreen],
  );

  const isPlaying = state === 'playing';
  const showBigPlay = state === 'ready' || state === 'paused' || state === 'ended';

  return (
    <div
      className="player"
      onKeyDown={onKeyDown}
      tabIndex={0}
      role="group"
      aria-label="Video pleer"
    >
      <div className="player__stage">
        <video
          ref={videoRef}
          className="player__video"
          src={src}
          playsInline
          loop={loop}
          preload="metadata"
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
          onCanPlay={() => setState((s) => (s === 'loading' ? 'ready' : s))}
          onPlay={() => setState('playing')}
          onPause={() => setState((s) => (s === 'ended' ? s : 'paused'))}
          onEnded={() => setState('ended')}
          onTimeUpdate={(e) => setCurrent(e.currentTarget.currentTime)}
          onError={() => setState('error')}
        />

        {state === 'loading' && (
          <div className="player__overlay">
            <span className="player__spinner" aria-hidden="true" />
            <span>Video yuklanmoqda…</span>
          </div>
        )}

        {state === 'error' && (
          <div className="player__overlay" role="alert">
            <span aria-hidden="true">⚠</span>
            <span>Videoni yuklab bo‘lmadi.</span>
          </div>
        )}

        {showBigPlay && (
          <div className="player__overlay" style={{ background: 'transparent' }}>
            <button
              className="player__big-play"
              onClick={togglePlay}
              aria-label={state === 'ended' ? 'Qayta o‘ynatish' : 'O‘ynatish'}
            >
              {state === 'ended' ? '↻' : '▶'}
            </button>
          </div>
        )}
      </div>

      <div className="player__controls">
        <button
          className="player__btn"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pauza' : 'O‘ynatish'}
        >
          {isPlaying ? '❚❚' : '▶'}
        </button>

        <span className="player__time" aria-hidden="true">
          {formatDuration(current)}
        </span>

        <input
          className="player__seek"
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={Math.min(current, duration || 0)}
          onChange={(e) => seek(Number(e.target.value))}
          aria-label="Vaqtni tanlash"
        />

        <span className="player__time" aria-hidden="true">
          {formatDuration(duration)}
        </span>

        <button className="player__btn" onClick={replay} aria-label="Qaytadan">
          ↻
        </button>
        <button
          className="player__btn"
          onClick={() => setLoop((l) => !l)}
          aria-pressed={loop}
          aria-label="Takrorlash rejimi"
          title="Takrorlash"
        >
          ⟳
        </button>
        <button
          className="player__btn"
          onClick={toggleFullscreen}
          aria-label="To‘liq ekran"
          title="To‘liq ekran"
        >
          ⛶
        </button>
      </div>
    </div>
  );
}

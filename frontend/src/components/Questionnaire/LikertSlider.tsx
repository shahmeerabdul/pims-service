import React, { useState, useRef, useEffect } from 'react';

interface Option {
  id: string;
  label: string;
  numeric_value: number;
  order: number;
}

interface LikertSliderProps {
  options: Option[];
  value?: number;
  onChange: (value: number) => void;
}

const LikertSlider: React.FC<LikertSliderProps> = ({ options, value, onChange }) => {
  const sortedOptions = [...options].sort((a, b) => a.numeric_value - b.numeric_value);
  const min = sortedOptions[0]?.numeric_value || 0;
  const max = sortedOptions[sortedOptions.length - 1]?.numeric_value || 10;
  
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef<HTMLDivElement>(null);

  const calculateValue = (clientX: number) => {
    if (!sliderRef.current) return;
    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const rawValue = min + percentage * (max - min);
    
    // Snap to nearest integer (or closest available numeric_value)
    const snappedValue = Math.round(rawValue);
    onChange(snappedValue);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    calculateValue(e.clientX);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setIsDragging(true);
    calculateValue(e.touches[0].clientX);
  };

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (isDragging) calculateValue(e.clientX);
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (isDragging) calculateValue(e.touches[0].clientX);
    };
    const handleUp = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleUp);
      window.addEventListener('touchmove', handleTouchMove);
      window.addEventListener('touchend', handleUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleUp);
    };
  }, [isDragging]);

  const percentage = (( (value || min) - min) / (max - min)) * 100;

  const parseAnchor = (lbl: string) => {
    if (lbl.includes('|')) {
      const [en, ur] = lbl.split('|').map(p => p.trim());
      return { en: en.replace(/^\d+\s*-\s*/, ''), ur };
    }
    return { en: lbl.replace(/^\d+\s*-\s*/, ''), ur: '' };
  };

  const minAnchor = parseAnchor(sortedOptions[0]?.label || '');
  const maxAnchor = parseAnchor(sortedOptions[sortedOptions.length - 1]?.label || '');

  return (
    <div className="py-4 px-4 select-none">
      <div
        ref={sliderRef}
        className="relative h-2 bg-zinc-200 rounded-full cursor-pointer mb-10"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        {/* Track highlight */}
        <div
          className="absolute h-full bg-zinc-700 rounded-full transition-all duration-75"
          style={{ width: `${percentage}%` }}
        />

        {/* Handle */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 -ml-3 w-6 h-6 bg-zinc-700 rounded-full shadow-lg transition-transform duration-75 ${isDragging ? 'scale-125' : ''}`}
          style={{ left: `${percentage}%` }}
        >
          {isDragging && (
             <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-zinc-800 text-white text-xs font-medium py-1 px-2.5 rounded-md whitespace-nowrap">
                {value ?? min}
             </div>
          )}
        </div>
      </div>

      {/* Anchor labels above 0 and max */}
      <div className="flex justify-between px-1 mb-1.5 pointer-events-none">
        <div className="flex flex-col items-start max-w-[42%]">
          <span className="text-[11px] font-semibold text-zinc-600 leading-tight">{minAnchor.en}</span>
          {minAnchor.ur && <span className="text-[11px] font-medium text-zinc-400 font-urdu leading-tight" dir="rtl">{minAnchor.ur}</span>}
        </div>
        <div className="flex flex-col items-end max-w-[42%] text-right">
          <span className="text-[11px] font-semibold text-zinc-600 leading-tight">{maxAnchor.en}</span>
          {maxAnchor.ur && <span className="text-[11px] font-medium text-zinc-400 font-urdu leading-tight" dir="rtl">{maxAnchor.ur}</span>}
        </div>
      </div>

      <div className="flex justify-between gap-1 px-1">
        {sortedOptions.map((opt) => (
          <button
            key={opt.id}
            onClick={() => onChange(opt.numeric_value)}
            className={`flex-1 flex flex-col items-center py-3 border rounded-lg transition-all duration-200 ${
              value === opt.numeric_value
                ? 'bg-zinc-800 border-zinc-700 text-white shadow-md -translate-y-0.5'
                : 'bg-white border-zinc-200 text-zinc-700 hover:border-zinc-300 hover:shadow-sm'
            }`}
          >
            <span className="text-lg font-bold">{opt.numeric_value}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default LikertSlider;

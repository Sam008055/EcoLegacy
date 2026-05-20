import { useState } from 'react';
import { X, Star, Send } from 'lucide-react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (rating: number, comment: string) => void;
}

export default function FeedbackModal({ isOpen, onClose, onSubmit }: FeedbackModalProps) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = () => {
    onSubmit(rating, comment);
    setSubmitted(true);
    setTimeout(() => {
      onClose();
      // Reset after closing
      setTimeout(() => {
        setSubmitted(false);
        setRating(0);
        setComment('');
      }, 300);
    }, 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-300">
      <div className="bg-zinc-900 border border-zinc-800/60 rounded-3xl p-6 w-full max-w-md shadow-2xl relative animate-in zoom-in-95 duration-300 overflow-hidden">
        
        {/* Subtle gradient background effect */}
        <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-indigo-500/10 to-transparent pointer-events-none" />

        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-zinc-500 hover:text-white bg-zinc-800/50 hover:bg-zinc-800 rounded-full transition-all"
        >
          <X size={16} />
        </button>
        
        {submitted ? (
          <div className="py-12 flex flex-col items-center justify-center text-center animate-in fade-in slide-in-from-bottom-4">
            <div className="w-16 h-16 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center mb-4">
              <Star size={32} className="fill-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Thank You!</h2>
            <p className="text-zinc-400">Your feedback helps us improve the experience.</p>
          </div>
        ) : (
          <div className="relative z-10">
            <div className="mb-8 text-center pt-4">
              <h2 className="text-2xl font-bold text-white mb-2">How was your experience?</h2>
              <p className="text-sm text-zinc-400">Help us improve the AI's responses and voice.</p>
            </div>

            <div className="mb-8 flex justify-center gap-3">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onMouseEnter={() => setHoveredRating(star)}
                  onMouseLeave={() => setHoveredRating(0)}
                  onClick={() => setRating(star)}
                  className="p-2 transition-transform hover:scale-125 focus:outline-none"
                >
                  <Star 
                    size={36} 
                    className={`${(hoveredRating || rating) >= star ? 'fill-indigo-400 text-indigo-400 drop-shadow-[0_0_8px_rgba(129,140,248,0.5)]' : 'text-zinc-700'} transition-all duration-200`} 
                  />
                </button>
              ))}
            </div>

            <div className="mb-6">
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Tell us what you liked or what could be better..."
                className="w-full h-28 bg-zinc-950/50 border border-zinc-800 rounded-2xl p-4 text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none transition-all"
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={rating === 0}
              className="w-full py-4 px-4 bg-white text-zinc-900 font-bold rounded-2xl hover:bg-zinc-200 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_25px_rgba(255,255,255,0.2)] disabled:shadow-none"
            >
              <Send size={18} />
              Submit Feedback
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

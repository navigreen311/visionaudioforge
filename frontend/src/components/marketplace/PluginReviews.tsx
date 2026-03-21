'use client';

import { useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Review {
  id: string;
  user: string;
  avatar: string;
  rating: number;
  date: string;
  comment: string;
  helpful: number;
}

interface RatingBreakdown {
  stars: number;
  count: number;
  percentage: number;
}

interface PluginReviewsProps {
  pluginName: string;
  avgRating: number;
  totalReviews: number;
  reviews: Review[];
  ratingBreakdown: RatingBreakdown[];
}

// ---------------------------------------------------------------------------
// Stars helper
// ---------------------------------------------------------------------------

function Stars({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'lg' }) {
  const cls = size === 'lg' ? 'h-5 w-5' : 'h-4 w-4';
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <svg
          key={n}
          className={`${cls} ${n <= Math.round(rating) ? 'text-yellow-400' : 'text-gray-300'}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Interactive star picker
// ---------------------------------------------------------------------------

function StarPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const [hover, setHover] = useState(0);
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(n)}
          className="focus:outline-none"
        >
          <svg
            className={`h-6 w-6 transition-colors ${
              n <= (hover || value) ? 'text-yellow-400' : 'text-gray-300'
            }`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </button>
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PluginReviews({
  pluginName,
  avgRating,
  totalReviews,
  reviews,
  ratingBreakdown,
}: PluginReviewsProps) {
  const [showForm, setShowForm] = useState(false);
  const [newRating, setNewRating] = useState(0);
  const [newComment, setNewComment] = useState('');

  const handleSubmit = () => {
    // In production this would POST to the API
    setShowForm(false);
    setNewRating(0);
    setNewComment('');
  };

  return (
    <div className="space-y-6">
      {/* Rating summary */}
      <div className="flex gap-8 items-start">
        {/* Big average */}
        <div className="text-center">
          <p className="text-5xl font-bold text-gray-900">{avgRating.toFixed(1)}</p>
          <Stars rating={avgRating} size="lg" />
          <p className="text-xs text-gray-500 mt-1">
            {totalReviews} review{totalReviews !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Breakdown bars */}
        <div className="flex-1 space-y-1.5">
          {ratingBreakdown.map((row) => (
            <div key={row.stars} className="flex items-center gap-2 text-sm">
              <span className="w-3 text-right text-gray-600">{row.stars}</span>
              <svg className="h-3.5 w-3.5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-400 rounded-full transition-all"
                  style={{ width: `${row.percentage}%` }}
                />
              </div>
              <span className="w-8 text-xs text-gray-500 text-right">{row.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Write a review */}
      <div>
        {!showForm ? (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 text-sm font-medium border border-brand-300 text-brand-600 rounded-lg hover:bg-brand-50 transition-colors"
          >
            Write a review
          </button>
        ) : (
          <div className="border border-gray-200 rounded-xl p-4 space-y-3 bg-gray-50">
            <p className="text-sm font-semibold text-gray-900">
              Review {pluginName}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Your rating:</span>
              <StarPicker value={newRating} onChange={setNewRating} />
            </div>
            <textarea
              rows={3}
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Share your experience..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-1 focus:ring-brand-500 focus:outline-none resize-none"
            />
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={newRating === 0 || !newComment.trim()}
                className="px-4 py-1.5 text-sm font-medium bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Submit
              </button>
              <button
                onClick={() => {
                  setShowForm(false);
                  setNewRating(0);
                  setNewComment('');
                }}
                className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Review list */}
      <div className="space-y-4">
        {reviews.map((review) => (
          <div
            key={review.id}
            className="border border-gray-200 rounded-xl p-4 bg-white space-y-2"
          >
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600">
                {review.avatar}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{review.user}</p>
                <p className="text-xs text-gray-400">{review.date}</p>
              </div>
              <Stars rating={review.rating} />
            </div>
            <p className="text-sm text-gray-700">{review.comment}</p>
            <button className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
              Helpful ({review.helpful})
            </button>
          </div>
        ))}
        {reviews.length === 0 && (
          <p className="text-center text-sm text-gray-400 py-6">
            No reviews yet. Be the first to review!
          </p>
        )}
      </div>
    </div>
  );
}

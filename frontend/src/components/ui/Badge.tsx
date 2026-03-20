"use client";

import React from "react";

const variantClasses: Record<string, string> = {
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  error: "bg-red-100 text-red-800",
  danger: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
  neutral: "bg-gray-100 text-gray-800",
  default: "bg-gray-100 text-gray-800",
};

export interface BadgeProps {
  variant?: string;
  className?: string;
  children: React.ReactNode;
}

export default function Badge({ variant = "neutral", className, children }: BadgeProps) {
  const variantClass = variantClasses[variant] || variantClasses.neutral;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClass}${className ? ` ${className}` : ""}`}
    >
      {children}
    </span>
  );
}

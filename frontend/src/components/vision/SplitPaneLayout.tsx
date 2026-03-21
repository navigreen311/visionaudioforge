"use client";

import React from "react";

interface SplitPaneLayoutProps {
  left: React.ReactNode;
  right: React.ReactNode;
}

export default function SplitPaneLayout({ left, right }: SplitPaneLayoutProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-[45fr_55fr]">
      <div>{left}</div>
      <div className="md:sticky md:top-4 md:self-start">{right}</div>
    </div>
  );
}

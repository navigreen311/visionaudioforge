"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import WizardStep1 from "./WizardStep1";
import WizardStep2 from "./WizardStep2";
import WizardStep3 from "./WizardStep3";
import WizardStep4 from "./WizardStep4";

const TOTAL_STEPS = 4;
const STORAGE_KEY = "vaf_onboarding_complete";

export default function OnboardingWizard() {
  const router = useRouter();
  const { addToast } = useToast();
  const [visible, setVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [destination, setDestination] = useState("/");

  useEffect(() => {
    try {
      const done = localStorage.getItem(STORAGE_KEY);
      if (done !== "true") {
        setVisible(true);
      }
    } catch {
      // localStorage unavailable — skip onboarding
    }
  }, []);

  const finish = (dest?: string) => {
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // ignore
    }
    setVisible(false);
    const target = dest ?? destination;
    router.push(target);
    addToast("success", "Setup complete! Welcome to VisionAudioForge.");
  };

  const skip = () => {
    try {
      localStorage.setItem(STORAGE_KEY, "true");
    } catch {
      // ignore
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60">
      <div className="relative w-full max-w-2xl rounded-2xl bg-white shadow-2xl">
        {/* Skip link */}
        <button
          onClick={skip}
          className="absolute right-4 top-4 text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          Skip setup
        </button>

        {/* Progress dots */}
        <div className="flex justify-center gap-2 pt-6">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <span
              key={i}
              className={`h-2 w-2 rounded-full transition-colors ${
                i === currentStep ? "bg-blue-600" : "bg-gray-300"
              }`}
            />
          ))}
        </div>

        {/* Steps */}
        {currentStep === 0 && (
          <WizardStep1 onNext={() => setCurrentStep(1)} />
        )}
        {currentStep === 1 && (
          <WizardStep2
            onNext={() => {
              setCurrentStep(2);
            }}
          />
        )}
        {currentStep === 2 && (
          <WizardStep3
            onNext={(route) => {
              setDestination(route);
              setCurrentStep(3);
            }}
          />
        )}
        {currentStep === 3 && (
          <WizardStep4
            onComplete={() => finish()}
            onSkip={() => finish()}
          />
        )}
      </div>
    </div>
  );
}

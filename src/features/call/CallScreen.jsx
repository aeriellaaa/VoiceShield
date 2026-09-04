import { useState } from "react";
import { useRiskStream } from "../../hooks/useRiskStream";
import { riskConfig } from "./riskConfig";
import { Badge } from "../../ui/Badge";
import { Card } from "../../ui/Card";
import { Label } from "../../ui/Label";
import { AuroraBackground } from "../../ui/AuroraBackground";
import ChallengeCard from "../challenge/ChallengeCard";
import PanicCard from "../panic/PanicCard";
import BranchBreakdown from "./BranchBreakdown";

function CallScreen({ embedded = false }) {
  const {
    decision,
    status,
    setDemoScenario,
    analyzeUploadedFile,
    isAnalyzing
  } = useRiskStream();

  const [showPanic, setShowPanic] = useState(false);

  const risk = riskConfig[decision.decision];

  const barCount = 24;

  const bars = Array.from({ length: barCount }, (_, i) => {
    const seed =
      Math.sin(
        i * 12.9898 + decision.fused_score * 78.233
      ) * 43758.5453;

    const wobble = seed - Math.floor(seed);

    const active =
      i / barCount < decision.fused_score;

    return {
      height: active
        ? 22 + wobble * 78
        : 12 + wobble * 10,
      active
    };
  });

  const meterColor =
    risk.tone === "verified"
      ? "bg-sage-deep"
      : risk.tone === "caution"
      ? "bg-gold-deep"
      : risk.tone === "alert"
      ? "bg-terracotta"
      : "bg-rose";

  const ringColor =
    risk.tone === "verified"
      ? "shadow-sage/30"
      : risk.tone === "caution"
      ? "shadow-gold/30"
      : risk.tone === "alert"
      ? "shadow-terracotta/30"
      : "shadow-rose/30";

  return (
    <div
      className={
        embedded
          ? "text-ink flex flex-col items-center gap-7 p-4 relative z-10"
          : "min-h-screen text-ink flex flex-col items-center justify-center gap-7 p-6 relative"
      }
    >
      {!embedded && <AuroraBackground />}

      <div className="w-full max-w-md flex flex-col items-center gap-7 relative z-10">

        {/* Call Status */}
        <div className="flex flex-col items-center gap-1.5">
          <Label>Incoming call</Label>

          {status === "error" && (
            <p className="text-terracotta text-xs flex items-center gap-1.5 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta" />
              Connection lost — showing last known state
            </p>
          )}

          {status === "connecting" && (
            <p className="text-sage-deep text-xs animate-pulse font-medium">
              Connecting to detection service…
            </p>
          )}
        </div>

        {/* Phone Number + Risk */}
        <div className="flex flex-col items-center gap-4">
          <h1
            className={`font-display font-semibold tracking-tight tabular-nums whitespace-nowrap ${
              embedded ? "text-2xl" : "text-5xl"
            }`}
          >
            {decision.number}
          </h1>

          <div
            className={`animate-float rounded-full shadow-[0_0_0_10px] ${ringColor}`}
          >
            <Badge tone={risk.tone}>
              {risk.label}
            </Badge>
          </div>
        </div>

        {/* Confidence Meter */}
        <div className="w-full flex flex-col items-center gap-2 pt-2">
          <div className="flex items-end gap-[3px] h-16 w-full max-w-xs justify-center">
            {bars.map((bar, i) => (
              <div
                key={i}
                className={`w-1.5 rounded-full transition-all duration-500 ${
                  bar.active ? meterColor : "bg-hairline"
                }`}
                style={{
                  height: `${bar.height}%`
                }}
              />
            ))}
          </div>

          <p className="text-sm text-ink-soft font-mono">
            confidence{" "}
            <span className="text-ink font-semibold tabular-nums">
              {(decision.fused_score * 100).toFixed(1)}%
            </span>
          </p>
        </div>

        {/* Explanation */}
        <Card className="w-full" hover>
          <Label className="mb-2">
            Why this decision
          </Label>

          <p className="text-sm text-ink leading-relaxed">
            {decision.explanation}
          </p>
        </Card>

        {/* Demo Controls */}
        <div className="w-full">
          <Label className="mb-2">
            Demo comparison
          </Label>

          <div className="flex gap-2">
            <button
              onClick={() => setDemoScenario("real")}
              className="flex-1 rounded-xl bg-sage-deep px-4 py-3 text-sm text-white transition hover:opacity-90"
            >
              Simulate real voice
            </button>

            <button
              onClick={() => setDemoScenario("clone")}
              className="flex-1 rounded-xl bg-terracotta px-4 py-3 text-sm text-white transition hover:opacity-90"
            >
              Simulate clone
            </button>
          </div>
        </div>

        {/* Real Audio Upload */}
        <div className="w-full">
          <Label className="mb-2">
            Test with real audio
          </Label>

          <label className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-hairline px-4 py-3 text-sm text-ink-soft cursor-pointer hover:border-sage-deep transition">
            {isAnalyzing ? "Analyzing…" : "Upload a voice recording (.wav)"}
            <input
              type="file"
              accept="audio/wav,audio/*"
              className="hidden"
              disabled={isAnalyzing}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) analyzeUploadedFile(file);
              }}
            />
          </label>
        </div>

        {/* Challenge */}
        <ChallengeCard
          challengeType={decision.challenge_type}
          onResult={(r) =>
            console.log("Challenge result:", r)
          }
        />

        {/* Branch Breakdown */}
        <BranchBreakdown
          branchScores={decision.branch_scores}
        />

        {/* Panic */}
        {!showPanic ? (
          <button
            onClick={() => setShowPanic(true)}
            className="text-xs text-ink-soft hover:text-terracotta underline underline-offset-4 transition-colors"
          >
            Simulate: this looks like an emotional/panic-inducing call
          </button>
        ) : (
          <PanicCard />
        )}
      </div>
    </div>
  );
}

export default CallScreen;
(function () {
  // --- 1. Ask for precise target time (HH:MM:SS.mmm) ---
  const targetStr = prompt(
    "Enter target time (24h, include milliseconds):\nExample: 08:59:59.900"
  );
  if (!targetStr) {
    console.log("No target time entered. Aborting.");
    return;
  }

  // Parse HH:MM:SS.mmm
  const timeMatch = targetStr.match(/^(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$/);
  if (!timeMatch) {
    console.log("Invalid time format. Use HH:MM:SS.mmm (milliseconds optional).");
    return;
  }

  const [, H, M, S, MS = "0"] = timeMatch;
  const hours = Number(H);
  const minutes = Number(M);
  const seconds = Number(S);
  const millis = Number(MS.padEnd(3, "0")); // ensures .9 → 900, .99 → 990

  // --- 2. Optional extra delay after target time ---
  const delayMsInput = prompt("Extra delay AFTER hitting time (ms):", "0");
  const extraDelay = Number(delayMsInput);
  if (Number.isNaN(extraDelay)) {
    console.log("Invalid delay. Aborting.");
    return;
  }

  // --- 3. Compute exact target timestamp ---
  const now = new Date();
  const target = new Date();

  target.setHours(hours, minutes, seconds, millis);

  // If target time already passed today, schedule for tomorrow
  if (target.getTime() <= now.getTime()) {
    target.setDate(target.getDate() + 1);
  }

  const msUntil = target.getTime() - now.getTime();

  console.log("Current time: ", now.toISOString());
  console.log("Target time:  ", target.toISOString());
  console.log("Milliseconds until target: ", msUntil);
  console.log("Extra delay (ms): ", extraDelay);
  console.log("Total wait (ms): ", msUntil + extraDelay);

  // --- 4. Schedule click with precise timing ---
  setTimeout(() => {
    console.log(
      "Target time reached:",
      new Date().toISOString(),
      " -> waiting extra delay..."
    );

    setTimeout(() => {
      const btn = document.getElementById("ctl00_contentPlaceHolder_ibEnroll");
      if (btn) {
        console.log("CLICK at", new Date().toISOString());
        btn.click();
      } else {
        console.log("Register button not found at click time.");
      }
    }, extraDelay);

  }, msUntil);
})();
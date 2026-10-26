document.addEventListener("DOMContentLoaded", () => {
  const tabDeposit = document.getElementById("tab-deposit");
  const tabWithdraw = document.getElementById("tab-withdraw");
  const tabPin = document.getElementById("tab-pin");

  const atmForm = document.getElementById("atm-form");
  const pinForm = document.getElementById("pin-form");
  const actionType = document.getElementById("action-type");
  const amountLabel = document.getElementById("amount-label");
  const atmBtnText = document.getElementById("atm-btn-text");
  const atmSubmitBtn = document.getElementById("atm-submit-btn");
  const txAlert = document.getElementById("tx-alert");
  const balanceDisplay = document.getElementById("user-balance");

  // Tab switching logic
  if (tabDeposit && tabWithdraw && tabPin) {
    const resetTabs = () => {
      [tabDeposit, tabWithdraw, tabPin].forEach(t => {
        t.className = "atm-tab px-3 py-1.5 rounded-lg text-xs font-mono-tech font-bold bg-slate-800 text-slate-400 border border-slate-700";
      });
      txAlert.classList.add("hidden");
    };

    tabDeposit.addEventListener("click", () => {
      resetTabs();
      tabDeposit.className = "atm-tab px-3 py-1.5 rounded-lg text-xs font-mono-tech font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40";
      atmForm.classList.remove("hidden");
      pinForm.classList.add("hidden");
      actionType.value = "DEPOSIT";
      amountLabel.innerText = "Deposit Amount ($)";
      atmBtnText.innerText = "AUTHORIZE DEPOSIT";
      atmSubmitBtn.className = "w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-mono-tech font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2";
    });

    tabWithdraw.addEventListener("click", () => {
      resetTabs();
      tabWithdraw.className = "atm-tab px-3 py-1.5 rounded-lg text-xs font-mono-tech font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40";
      atmForm.classList.remove("hidden");
      pinForm.classList.add("hidden");
      actionType.value = "WITHDRAW";
      amountLabel.innerText = "Withdrawal Amount ($)";
      atmBtnText.innerText = "AUTHORIZE WITHDRAWAL";
      atmSubmitBtn.className = "w-full py-3 bg-rose-600 hover:bg-rose-500 text-white font-mono-tech font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2";
    });

    tabPin.addEventListener("click", () => {
      resetTabs();
      tabPin.className = "atm-tab px-3 py-1.5 rounded-lg text-xs font-mono-tech font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/40";
      atmForm.classList.add("hidden");
      pinForm.classList.remove("hidden");
    });
  }

  // Handle Deposit / Withdraw execution
  if (atmForm) {
    atmForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const type = actionType.value;
      const amount = document.getElementById("atm-amount").value;
      const pin = document.getElementById("atm-pin").value;
      const endpoint = type === "DEPOSIT" ? "/api/deposit" : "/api/withdraw";

      atmSubmitBtn.disabled = true;
      atmBtnText.innerText = "VERIFYING SECURITY PIN & DISPATCHING...";

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amount, pin })
        });
        const data = await res.json();

        txAlert.classList.remove("hidden");
        if (data.success) {
          txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-emerald-950/70 border-emerald-600 text-emerald-200";
          txAlert.innerHTML = `<strong>SECURITY APPROVED:</strong> ${data.message} <br><span class="text-[10px] text-slate-400">RECEIPT TOKEN: #${data.security_token}</span>`;
          balanceDisplay.innerText = data.new_balance;
          atmForm.reset();
          setTimeout(() => window.location.reload(), 1400);
        } else {
          txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-rose-950/70 border-rose-600 text-rose-200";
          txAlert.innerText = `SECURITY REJECTED: ${data.message}`;
        }
      } catch (err) {
        txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-rose-950/70 border-rose-600 text-rose-200";
        txAlert.innerText = "Network Error: Ledger connection lost.";
      } finally {
        atmSubmitBtn.disabled = false;
        atmBtnText.innerText = type === "DEPOSIT" ? "AUTHORIZE DEPOSIT" : "AUTHORIZE WITHDRAWAL";
      }
    });
  }

  // Handle Change PIN execution
  if (pinForm) {
    pinForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const old_pin = document.getElementById("old-pin").value;
      const new_pin = document.getElementById("new-pin").value;

      try {
        const res = await fetch("/api/change-pin", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ old_pin, new_pin })
        });
        const data = await res.json();

        txAlert.classList.remove("hidden");
        if (data.success) {
          txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-emerald-950/70 border-emerald-600 text-emerald-200";
          txAlert.innerText = data.message;
          pinForm.reset();
        } else {
          txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-rose-950/70 border-rose-600 text-rose-200";
          txAlert.innerText = data.message;
        }
      } catch (err) {
        txAlert.className = "mb-4 text-xs font-mono-tech p-3 rounded-xl border bg-rose-950/70 border-rose-600 text-rose-200";
        txAlert.innerText = "Failed to update PIN.";
      }
    });
  }
});
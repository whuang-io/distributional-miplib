// Copy buttons for BibTeX blocks
document.querySelectorAll("pre").forEach((pre) => {
  const btn = document.createElement("button");
  btn.className = "copy-btn";
  btn.type = "button";
  btn.textContent = "Copy";
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(pre.querySelector("code")?.innerText ?? pre.innerText);
      btn.textContent = "Copied";
    } catch {
      btn.textContent = "Failed";
    }
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  });
  pre.appendChild(btn);
});

// Close the Domains dropdown when clicking elsewhere
document.addEventListener("click", (e) => {
  document.querySelectorAll("details.dd[open]").forEach((d) => {
    if (!d.contains(e.target)) d.removeAttribute("open");
  });
});

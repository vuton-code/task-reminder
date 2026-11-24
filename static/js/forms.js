(() => {
  const notice = document.querySelector("[data-save-notice]");
  if (notice) { notice.tabIndex = -1; notice.focus(); }
  const firstError = document.querySelector(".errorlist");
  if (firstError) { firstError.tabIndex = -1; firstError.setAttribute("role", "alert"); firstError.focus(); }
  const announcer = document.createElement("div");
  announcer.className = "visually-hidden";
  announcer.setAttribute("aria-live", "polite");
  document.querySelector("main").append(announcer);
  const serverErrors = new WeakSet();
  let timer;
  const controls = [...document.querySelectorAll("input:not([type=hidden]), select, textarea")];
  const nativeState = CSS.supports("selector(:user-invalid)");
  const sync = (field, announce = false, failedSubmit = false) => {
    if (!controls.includes(field) || serverErrors.has(field)) return;
    const invalid = failedSubmit || (nativeState && field.matches(":user-invalid"));
    field.setAttribute("aria-invalid", String(invalid));
    let error = document.getElementById(field.dataset.clientError);
    if (invalid && !error) {
      error = document.createElement("span");
      error.id = field.id + "-client-error";
      error.className = "form-client-error";
      field.dataset.clientError = error.id;
      field.after(error);
    }
    const ids = (field.getAttribute("aria-describedby") || "").split(/\s+/).filter(id => id && id !== field.dataset.clientError);
    if (error) {
      error.hidden = !invalid;
      error.textContent = invalid ? field.validationMessage : "";
      if (invalid) ids.push(error.id);
    }
    if (ids.length) field.setAttribute("aria-describedby", ids.join(" "));
    else field.removeAttribute("aria-describedby");
    if (announce && invalid && error) {
      clearTimeout(timer); announcer.textContent = "";
      timer = setTimeout(() => { announcer.textContent = error.textContent; }, 500);
    } else if (!invalid) {
      clearTimeout(timer); announcer.textContent = "";
    }
  };
  controls.forEach((field, index) => {
    if (!field.id) field.id = "form-control-" + index;
    for (const label of field.labels || []) label.htmlFor = field.id;
    if (field.getAttribute("aria-invalid") === "true") serverErrors.add(field);
    else field.setAttribute("aria-invalid", "false");
    if (field.type === "password") {
      const toggle = document.createElement("button");
      toggle.type = "button"; toggle.className = "text-button password-toggle";
      toggle.textContent = "Show " + (field.labels[0]?.textContent.replace(/:$/, "").toLowerCase() || "password");
      toggle.setAttribute("aria-controls", field.id);
      toggle.setAttribute("aria-pressed", "false");
      toggle.addEventListener("click", () => {
        const visible = field.type === "password";
        field.type = visible ? "text" : "password";
        toggle.setAttribute("aria-pressed", String(visible));
      });
      field.after(toggle);
    }
  });
  document.addEventListener("blur", event => sync(event.target, true), true);
  document.addEventListener("change", event => sync(event.target, true), true);
  document.addEventListener("input", event => sync(event.target));
  document.addEventListener("invalid", event => sync(event.target, false, true), true);
  document.addEventListener("reset", event => setTimeout(() => [...event.target.elements].forEach(field => sync(field))), true);
})();

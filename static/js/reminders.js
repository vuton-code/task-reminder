(() => {
  const containers = document.querySelectorAll("[data-reminders]");
  if (!containers.length) return;
  let generation = 0;
  let controller;
  async function refresh() {
    if (document.hidden || !navigator.onLine) return;
    const current = ++generation;
    if (controller) controller.abort();
    controller = new AbortController();
    try {
      const response = await fetch("/reminders/due?cursor=" + (containers[0].dataset.offset || "0"), {credentials: "same-origin", cache: "no-store", signal: controller.signal});
      if ([401, 403, 404].includes(response.status)) {
        containers.forEach(container => container.replaceChildren());
        window.location.assign("/accounts/login");
        return;
      }
      if (!response.ok) throw new Error("Unable to refresh");
      const data = await response.json();
      if (current !== generation) return;
      document.querySelectorAll("[data-next-reminders]").forEach(link => {
        link.hidden = data.next_cursor === null;
        link.href = "/reminders?cursor=" + (data.next_cursor || "0");
      });
      containers.forEach(container => {
        const signature = JSON.stringify(data.items);
        if (container.dataset.signature === signature) return;
        container.dataset.signature = signature;
        const fragment = document.createDocumentFragment();
        for (const item of data.items) {
          const link = document.createElement("a");
          link.className = "reminder-item";
          link.href = item.task_url;
          const label = document.createElement("span");
          label.className = "reminder-label";
          label.textContent = "DUE REMINDER";
          const title = document.createElement("strong");
          title.textContent = item.title;
          link.append(label, title);
          function metadata(prefix, value, stamp) {
            const row = document.createElement("span");
            row.className = "reminder-meta";
            row.append(document.createTextNode(prefix));
            if (stamp) {
              const time = document.createElement("time");
              time.dateTime = stamp;
              time.textContent = value;
              row.append(time);
            } else row.append(document.createTextNode(value));
            link.append(row);
          }
          metadata("Due ", item.scheduled_label, item.scheduled_at);
          if (item.creator_name) metadata("Assigned by ", item.creator_name);
          metadata("Created ", item.created_label, item.created_at);
          if (item.assigned_at) metadata("Assigned ", item.assigned_label, item.assigned_at);
          fragment.append(link);
        }
        if (!data.items.length) {
          const text = document.createElement("p");
          text.className = "muted";
          text.textContent = "You’re all caught up. Due reminders will appear here.";
          fragment.append(text);
        }
        container.replaceChildren(fragment);
      });
      document.querySelectorAll("[data-reminder-status]").forEach(node => node.textContent = "");
    } catch (error) {
      if (error.name === "AbortError") return;
      document.querySelectorAll("[data-reminder-status]").forEach(node => node.textContent = "Updates paused. Reconnecting…");
    }
  }
  setInterval(refresh, 2000);
  document.addEventListener("visibilitychange", refresh);
  window.addEventListener("online", refresh);
  window.addEventListener("offline", () => document.querySelectorAll("[data-reminder-status]").forEach(node => node.textContent = "Offline. Reminders may be out of date."));
  window.addEventListener("focus", refresh);
  refresh();
})();

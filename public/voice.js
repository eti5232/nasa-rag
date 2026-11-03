// שלב 14 - הקלטת שאלה בקול (Web Speech API). להסרה: למחוק את הקובץ הזה ואת השורה custom_js ב-.chainlit/config.toml
(function () {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return;

  let recognition = null;
  let listening = false;
  let lang = "he-IL";

  const mic = document.createElement("button");
  mic.id = "voice-mic";
  mic.type = "button";
  mic.title = "הקלטת שאלה בקול";
  mic.textContent = "🎤";

  const langBtn = document.createElement("button");
  langBtn.id = "voice-lang";
  langBtn.type = "button";
  langBtn.title = "שפת ההקלטה";
  langBtn.textContent = "עב";

  const box = document.createElement("div");
  box.id = "voice-box";
  box.append(mic, langBtn);

  function insertText(input, text) {
    input.focus();
    document.execCommand("insertText", false, text);
  }

  function stop() {
    listening = false;
    mic.classList.remove("on");
    if (recognition) recognition.stop();
  }

  function start() {
    const input = document.getElementById("chat-input");
    if (!input) return;
    recognition = new Recognition();
    recognition.lang = lang;
    recognition.interimResults = false;
    recognition.continuous = true;
    recognition.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) insertText(input, e.results[i][0].transcript + " ");
      }
    };
    // הדפדפן עלול לעצור לבד אחרי שקט ארוך; כל עוד המשתמשת לא לחצה לעצור, ממשיכים להקשיב
    recognition.onend = () => (listening ? recognition.start() : stop());
    recognition.onerror = (e) => {
      if (e.error !== "no-speech") stop();
    };
    listening = true;
    mic.classList.add("on");
    recognition.start();
  }

  mic.addEventListener("click", () => (listening ? stop() : start()));
  langBtn.addEventListener("click", () => {
    lang = lang === "he-IL" ? "en-US" : "he-IL";
    langBtn.textContent = lang === "he-IL" ? "עב" : "EN";
  });

  // הכפתורים נכנסים לשורת הכפתורים של תיבת השאלה, ליד כפתור השליחה.
  // Chainlit בונה מחדש את התיבה בכל מעבר מסך, לכן בודקים שוב בכל שינוי בדף.
  function attach() {
    const send = document.getElementById("chat-submit");
    if (send && send.parentElement && !send.parentElement.contains(box)) {
      send.parentElement.insertBefore(box, send);
    }
  }
  new MutationObserver(attach).observe(document.body, { childList: true, subtree: true });
  attach();
})();

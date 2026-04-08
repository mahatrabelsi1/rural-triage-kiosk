export default function AvatarAssistant() {
  return (
    <aside className="avatar-assistant" aria-label="Virtual nurse assistant">
      <div className="avatar-panel-head">
        <h2>Virtual Nurse</h2>
        <p>Guidance companion</p>
      </div>
      <video
        className="avatar-video"
        src="/assets/Nurse_GIF_Generation_Request.mp4"
        autoPlay
        muted
        loop
        playsInline
      />
      <div className="avatar-caption">Assistant View</div>
    </aside>
  );
}

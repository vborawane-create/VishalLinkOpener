import pathlib, re
p = pathlib.Path("project/app/src/main/java/com/vishal/linkopener/MainActivity.java")
s = p.read_text()
# Replace the Google Docs viewer with a native PDF renderer and fixed bottom download action.
s = s.replace("import android.webkit.*;", "import android.webkit.*;\nimport android.graphics.pdf.PdfRenderer;\nimport android.os.ParcelFileDescriptor;\nimport java.net.HttpURLConnection;\nimport java.net.URL;\nimport java.io.File;\nimport java.io.FileOutputStream;")
start = s.index("  void viewer() {")
end = s.index("  void downloadPdf() {", start)
new = r'''  void viewer() {
    LinearLayout page = new LinearLayout(this);
    page.setOrientation(LinearLayout.VERTICAL);
    page.setBackgroundColor(BG);
    page.setPadding(0, dp(4), 0, 0);

    FrameLayout area = new FrameLayout(this);
    area.setBackgroundColor(Color.rgb(35,35,35));
    ProgressBar progress = new ProgressBar(this);
    progress.setIndeterminate(true);
    TextView loading = text("Loading Purchase Order...", 16, Color.WHITE, true);
    loading.setGravity(Gravity.CENTER);
    LinearLayout loadingBox = new LinearLayout(this);
    loadingBox.setGravity(Gravity.CENTER);
    loadingBox.setOrientation(LinearLayout.VERTICAL);
    loadingBox.addView(progress, lp(48,48));
    loadingBox.addView(loading, lp(-1,52));
    area.addView(loadingBox, new FrameLayout.LayoutParams(-1,-1));
    page.addView(area, new LinearLayout.LayoutParams(-1,0,1));

    Button download = new Button(this);
    download.setText("DOWNLOAD PDF");
    download.setTextSize(16);
    download.setTextColor(Color.WHITE);
    download.setAllCaps(false);
    download.setBackground(panel(RED, Color.rgb(177,7,32), 10));
    LinearLayout.LayoutParams downloadLp = lp(-1,56);
    downloadLp.setMargins(dp(12),dp(8),dp(12),dp(8));
    page.addView(download, downloadLp);
    download.setOnClickListener(v -> downloadPdf());
    setContentView(page);

    new Thread(() -> {
      HttpURLConnection conn = null;
      try {
        conn = (HttpURLConnection)new URL(pdfUrl).openConnection();
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(20000);
        conn.setInstanceFollowRedirects(true);
        conn.setRequestProperty("User-Agent","Mozilla/5.0");
        int code = conn.getResponseCode();
        String type = conn.getContentType();
        if (code != 200 || (type != null && !type.toLowerCase(Locale.ROOT).contains("pdf"))) {
          runOnUiThread(() -> {
            loadingBox.removeAllViews();
            TextView msg = text("PURCHASE ORDER NOT READY",18,Color.WHITE,true);
            msg.setGravity(Gravity.CENTER);
            loadingBox.addView(msg,lp(-1,100));
          });
          return;
        }
        File file = new File(getCacheDir(),"purchase_order.pdf");
        try (java.io.InputStream in=conn.getInputStream(); FileOutputStream out=new FileOutputStream(file)) {
          byte[] buf=new byte[8192]; int n;
          while((n=in.read(buf))!=-1) out.write(buf,0,n);
        }
        runOnUiThread(() -> {
          try {
            loadingBox.removeAllViews();
            ParcelFileDescriptor fd = ParcelFileDescriptor.open(file,ParcelFileDescriptor.MODE_READ_ONLY);
            PdfRenderer renderer = new PdfRenderer(fd);
            if (renderer.getPageCount()==0) throw new Exception("Empty PDF");
            PdfPageView pdfView = new PdfPageView(renderer);
            area.addView(pdfView,new FrameLayout.LayoutParams(-1,-1));
          } catch(Exception ex) {
            loadingBox.removeAllViews();
            TextView msg=text("PURCHASE ORDER NOT READY",18,Color.WHITE,true);
            msg.setGravity(Gravity.CENTER);
            loadingBox.addView(msg,lp(-1,100));
          }
        });
      } catch(Exception e) {
        runOnUiThread(() -> {
          loadingBox.removeAllViews();
          TextView msg=text("PURCHASE ORDER NOT READY",18,Color.WHITE,true);
          msg.setGravity(Gravity.CENTER);
          loadingBox.addView(msg,lp(-1,100));
        });
      } finally { if(conn!=null) conn.disconnect(); }
    }).start();
  }

  class PdfPageView extends View {
    private final PdfRenderer renderer;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    PdfPageView(PdfRenderer r) { super(MainActivity.this); renderer=r; setBackgroundColor(Color.rgb(45,45,45)); }
    @Override protected void onDraw(Canvas canvas) {
      super.onDraw(canvas);
      int y=dp(10);
      for(int i=0;i<renderer.getPageCount() && y<getHeight();i++) {
        try(PdfRenderer.Page page=renderer.openPage(i)) {
          float scale=Math.min((float)(getWidth()-dp(16))/page.getWidth(),1.5f);
          int w=Math.max(1,(int)(page.getWidth()*scale));
          int h=Math.max(1,(int)(page.getHeight()*scale));
          Bitmap bitmap=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
          bitmap.eraseColor(Color.WHITE);
          page.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
          canvas.drawBitmap(bitmap,dp(8),y,paint);
          y+=h+dp(10);
          bitmap.recycle();
        } catch(Exception ignored) { break; }
      }
    }
  }
'''
s = s[:start] + new + s[end:]
# imports required by native page drawing
s = s.replace("import android.graphics.Color;", "import android.graphics.Color;\nimport android.graphics.Canvas;\nimport android.graphics.Bitmap;\nimport android.graphics.Paint;")
# Permit network access on a background thread (network is already expected for this app).
p.write_text(s)
manifest = pathlib.Path("project/app/src/main/AndroidManifest.xml")
m = manifest.read_text()
if 'android.permission.INTERNET' not in m:
    m = m.replace("<manifest", '<manifest')
    m = re.sub(r'(<manifest[^>]*>)', r'\1\n    <uses-permission android:name="android.permission.INTERNET" />', m, count=1)
manifest.write_text(m)
print("Patched native PDF viewer, loading state, not-ready message, and bottom download button.")

[x86_64]
camera: v4l2src always-copy=false ! 
	capsfilter caps=video/x-raw-yuv,width=1280,height=720,framerate=30/1 ! 
	pyperf print-cpu-load=true name=camera ! 
	interpipesink sync=false async=false qos=false enable-last-buffer=false node-name=camera
unicast: interpipesrc name=src is-live=true format=3 ! 
	capsfilter caps=video/x-raw-yuv,width=1280,height=720 ! 
	videorate name=videorate drop-only=true ! 
	pyperf print-cpu-load=true name=unicast ! 
	x264enc name=encoder speed-preset=ultrafast bitrate=1000 ! queue ! 
	rtph264pay scan-mode=2 buffer-list=true ! queue ! 
	udpsink sync=false enable-last-buffer=false qos=false port=5000 host=127.0.0.1

[armv5tejl]
unicast: interpipesrc name=src is-live=true format=3 ! 
	 capsfilter caps=video/x-raw-yuv,width=1920,height=1088,format=(fourcc)NV12 ! 
	 videorate name=videorate drop-only=true max-rate=30 ! 
	 dmaiaccel ! dmaiperf name=unicast print-arm-load=true ! 
	 dmaienc_h264 name=encoder encodingpreset=2 ratecontrol=1 
	 name=encoder bytestream=true targetbitrate=1000000 idrinterval=90 intraframeinterval=30 ! 
	 rtph264pay scan-mode=0 buffer-list=true !
	 udpsink async=false sync=false enable-last-buffer=false qos=false port=5000 host=10.251.101.23
camera: v4l2src always-copy=false queue-size=6 chain-ipipe=false ! 
	capsfilter caps=video/x-raw-yuv,width=1920,height=1088,framerate=30/1,format=(fourcc)NV12 !
	dmaiperf name=camera print-arm-load=true !  
	interpipesink node-name=camera sync=false qos=false enable-last-buffer=false

[Test]
mockpipeline: mockdescription
realpipeline: fakesrc name=fakesrc0 ! fakesink
failpipeline: fakesrc ! fakesink state-error=2

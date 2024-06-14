import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

import WaveSurfer from 'https://cdn.jsdelivr.net/npm/wavesurfer.js@7/dist/wavesurfer.esm.js'

function get_position_style (ctx, widget_width, y, node_height) {
  const MARGIN = 4 // the margin around the html element

  /* Create a transform that deals with all the scrolling and zooming */
  const elRect = ctx.canvas.getBoundingClientRect()
  const transform = new DOMMatrix()
    .scaleSelf(
      elRect.width / ctx.canvas.width,
      elRect.height / ctx.canvas.height
    )
    .multiplySelf(ctx.getTransform())
    .translateSelf(MARGIN, MARGIN + y)

  return {
    transformOrigin: '0 0',
    transform: transform,
    left: `0`,
    top: '0',
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    // maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    // height: `${node_height * 0.3 - MARGIN * 2}px`,
    // background: '#EEEEEE',
    display: 'flex',
    flexDirection: 'column',
    // alignItems: 'center',
    justifyContent: 'space-around'
  }
}

//把文件转为url访问
const parseUrl = data => {
  let { filename, subfolder, type, prompt } = data
  return {
    url: api.apiURL(
      `/view?filename=${encodeURIComponent(
        filename
      )}&type=${type}&subfolder=${subfolder}${app.getPreviewFormatParam()}${app.getRandParam()}`
    ),
    prompt
  }
}

const createWaveSurfer = (wavesurfer, id,url) => {
  // Create an instance of WaveSurfer
  if (wavesurfer) {
    wavesurfer.destroy()
  }
  wavesurfer = WaveSurfer.create({
    container: '#' + id,
    waveColor: 'rgb(200, 0, 200)',
    progressColor: 'rgb(100, 0, 100)',
    // Set a bar width
    barWidth: 10,
    // Optionally, specify the spacing between bars
    barGap: 2,
    // And the bar radius
    barRadius: 6,
    url
  })

  wavesurfer._auto = true

  // 监听播放结束事件，重新开始播放以实现循环播放
  wavesurfer.on('finish', function () {
    // console.log(wavesurfer)
    if (wavesurfer._auto) wavesurfer.play()
  })

  wavesurfer.on('interaction', () => {
    wavesurfer._auto = false
    if (!wavesurfer.isPlaying()) wavesurfer.play()
  })

  // 获取当前播放时间的峰值
  wavesurfer.on('audioprocess', () => {
    if (wavesurfer.isPlaying()&&wavesurfer.getDecodedData()) {
      const channelData = wavesurfer.getDecodedData().getChannelData(0); 
      const currentTime = wavesurfer.getCurrentTime()
      // console.log(wavesurfer)
      const sampleRate = wavesurfer.getDecodedData().sampleRate

      // 定义要分析的时间窗口（例如1秒）
      const windowSize = 1
      const startSample = Math.floor(currentTime * sampleRate)
      const endSample = Math.min(
        startSample + windowSize * sampleRate,
        channelData.length
      )

      let peak = 0
      for (let i = startSample; i < endSample; i++) {
        const value = Math.abs(channelData[i])
        if (value > peak) {
          peak = value
        }
      }
      // console.log('Current Peak:', peak)
    }
  })

  return wavesurfer
}

//更新gui
function updateWaveWidgetValue (widgets, id, url, prompt, wavesurfer) {
  let widget = widgets.filter(w => w.name == 'AudioPlay')[0]
  // 手动更新widget值
  widget.value = [url, prompt]

  if (widget.div) {
    widget.div.querySelector('.wave').id = `AudioPlay_${id}`
  }

  wavesurfer = createWaveSurfer(wavesurfer, `AudioPlay_${id}`,url)

  wavesurfer.on('ready', duration => {
    console.log('Audio duration: ' + duration + ' seconds')
    if (widget.div) {
      widget.div.setAttribute('data-url', url)
      widget.div.querySelector('.link').setAttribute('href', url)
      widget.div.querySelector(
        '.info'
      ).innerHTML = `<span style="font-size: 12px;
      margin: 8px;">${duration.toFixed(
        2
      )} seconds</span> <br><span style="font-size: 14px;">${prompt||''}</span> <br>`
    }
  })
  
  
  wavesurfer.load(url)
  // console.log('updateWaveWidgetValue' ,url,wavesurfer)
  return wavesurfer
}

app.registerExtension({
  name: 'SoundLab.AudioPlay',
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'AudioPlay') {
      let that = this
      // console.log('that', that)

      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'div',
          name: 'AudioPlay',
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.div.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            )
          }
        }

        // console.log('AudioPlay nodeData', this)
        widget.div = $el('div', {})

        document.body.appendChild(widget.div)

        // wave
        const waveDiv = document.createElement('div')
        waveDiv.className = 'wave'
        waveDiv.style.minHeight = '172px'
        widget.div.appendChild(waveDiv)

        //prompt 相关信息展示
        const infoDiv = document.createElement('div')
        infoDiv.className = 'info'
        infoDiv.style.marginBottom = '20px'
        widget.div.appendChild(infoDiv)

        // 按钮的区域
        let btns = document.createElement('div')
        btns.className = 'btns'
        btns.style = `display: flex;
        width: 100%;
        justify-content: space-between;`
        widget.div.appendChild(btns)

        //play button
        const playBtn = document.createElement('a')
        playBtn.innerText = 'Play/Pause'

        playBtn.style = `
        display: flex;
        padding: 4px 15px;
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;
        color: var(--descrip-text);
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease 0s;
          `

        playBtn.addEventListener('click', e => {
          e.preventDefault()
          if (that[`wavesurfer_${this.id}`]) {
            that[`wavesurfer_${this.id}`]?.playPause()
            that[`wavesurfer_${this.id}`]._auto = true
          }
        })
        btns.appendChild(playBtn)

        const urlLink = document.createElement('a')
        urlLink.className = 'link'
        urlLink.innerText = 'URL'
        urlLink.setAttribute('target', '_blank')
        urlLink.style = `display: flex;
        padding: 4px 15px;
        background-color: var(--comfy-input-bg);
        border-radius: 8px;
        border-color: var(--border-color);
        border-style: solid;
        color: var(--descrip-text);
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease 0s;`
        // urlLink.style.minHeight = '200px'
        btns.appendChild(urlLink)


        //todo 导出视频 that[`wavesurfer_${this.id}`].renderer.exportImage('image/png',1,'dataURL')
        // https://github.com/diffusion-studio/ffmpeg-js


        this.addCustomWidget(widget)

        const onRemoved = this.onRemoved
        this.onRemoved = () => {
          widget.div.remove()
          return onRemoved?.()
        }

        this.size = [this.size[0], 280]
        this.serialize_widgets = true //需保存widget的值
      }

      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        onExecuted?.apply(this, arguments)
        const audio = message.audio
        console.log('#onExecuted', `AudioPlay_${this.id}`, message,audio)
        try {
          let { url, prompt } = parseUrl(audio[0])

          that[`wavesurfer_${this.id}`] = updateWaveWidgetValue(
            this.widgets,
            this.id,
            url,
            prompt,
            that[`wavesurfer_${this.id}`]
          )

          that[`wavesurfer_${this.id}`]?.playPause()
        } catch (error) {
          console.log(error)
        }
      }
    }
  },
  async loadedGraphNode (node, app) {
    if (node.type === 'AudioPlay') {
      let widget = node.widgets.filter(w => w.name == 'AudioPlay')[0]

      if (widget.value) {
        let [url, prompt] = widget.value

        this[`wavesurfer_${node.id}`] = updateWaveWidgetValue(
          node.widgets,
          node.id,
          url,
          prompt,
          this[`wavesurfer_${node.id}`]
        )
      }

      console.log('#loadedGraphNode', node)
    }
  }
})

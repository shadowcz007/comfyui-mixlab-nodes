import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'

let api_host = '127.0.0.1:8188'
let api_base = ''
let url = `http://${api_host}${api_base}`

async function getQueue () {
  try {
    const res = await fetch(`${url}/queue`)
    const data = await res.json()
    // console.log(data.queue_running,data.queue_pending)
    return {
      // Running action uses a different endpoint for cancelling
      Running: data.queue_running.length,
      Pending:data.queue_pending.length
    }
  } catch (error) {
    console.error(error)
    return { Running:0, Pending:0 }
  }
}

async function uploadFile (file) {
  try {
    const body = new FormData()
    body.append('image', file)
    body.append('overwrite', 'true')
    body.append('type', 'temp')

    const resp = await fetch(`${url}/upload/image`, {
      method: 'POST',
      body
    })

    if (resp.status === 200) {
      const data = await resp.json()
      let path = data.name
      if (data.subfolder) path = data.subfolder + '/' + path
      return path
    } else {
      alert(resp.status + ' - ' + resp.statusText)
    }
  } catch (error) {
    alert(error)
  }
}

async function shareScreenAndUpload (imgElement) {
  try {
    let webcamVideo = document.createElement('video')
    const mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true
    })

    webcamVideo.removeEventListener('timeupdate', videoTimeUpdateHandler)
    webcamVideo.srcObject = mediaStream
    webcamVideo.onloadedmetadata = () => {
      webcamVideo.play()
      webcamVideo.addEventListener('timeupdate', videoTimeUpdateHandler)
    }

    async function videoTimeUpdateHandler () {
      if (window._mixlab_screen_time) {
        console.log('loading')
        return
      };

      const {Pending}=await getQueue();
      if(Pending<5) document.querySelector('#queue-button').click();

      const videoW = webcamVideo.videoWidth
      const videoH = webcamVideo.videoHeight
      const aspectRatio = videoW / videoH
      const WIDTH = 512,
        HEIGHT = Math.round(WIDTH / aspectRatio)
      const canvas = new OffscreenCanvas(WIDTH, HEIGHT)

      const ctx = canvas.getContext('2d')
      ctx.drawImage(webcamVideo, 0, 0, videoW, videoH, 0, 0, WIDTH, HEIGHT)

      const blob = await canvas.convertToBlob({
        type: 'image/jpeg',
        quality: 1
      })

      var reader = new FileReader()
      reader.onload = function (event) {
        // console.log(imgElement)
        imgElement.src = event.target.result
        // console.log(event.target.result)
      } // data url!
      var source = reader.readAsDataURL(blob)

      const file = new File([blob], `screenshot_mixlab.jpeg`)
      window._mixlab_screen_time = true
      window._mixlab_screen_imagePath = await uploadFile(file)
      window._mixlab_screen_time = false
    }

    // window._mixlab_screen_time = setInterval(() => {
    //   context.drawImage(videoTrack, 0, 0, canvas.width, canvas.height)
    // }, 300)
  } catch (error) {
    alert('Error accessing screen stream: ' + error)
  }
}

/* 
A method that returns the required style for the html 
*/
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
    top: `0`,
    cursor: 'pointer',
    position: 'absolute',
    maxWidth: `${widget_width - MARGIN * 2}px`,
    maxHeight: `${node_height - MARGIN * 2}px`, // we're assuming we have the whole height of the node
    width: `${widget_width - MARGIN * 2}px`,
    height: `${node_height - MARGIN * 2}px`
  }
}

app.registerExtension({
  name: 'Mixlab.image.ScreenShareNode',
  getCustomWidgets (app) {
    return {
      CHEESE (node, inputName, inputData, app) {
        // We return an object containing a field CHEESE which has a function (taking node, name, data, app)
        const widget = {
          type: inputData[0], // the type, CHEESE
          name: inputName, // the name, slice
          size: [128, 72], // a default size
          draw (ctx, node, width, y) {
            // a method to draw the widget (ctx is a CanvasRenderingContext2D)
          },
          computeSize (...args) {
            return [128, 72] // a method to compute the current size of the widget
          },
          async serializeValue (nodeId, widgetIndex) {
            return window._mixlab_screen_imagePath
          }
        }
        //  widget.something = something;          // maybe adds stuff to it
        node.addCustomWidget(widget) // adds it to the node
        return widget // and returns it.
      }
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    if (nodeType.comfyClass == 'ScreenShare') {
      /* 
          Hijack the onNodeCreated call to add our widget
          */
      const orig_nodeCreated = nodeType.prototype.onNodeCreated
      nodeType.prototype.onNodeCreated = function () {
        orig_nodeCreated?.apply(this, arguments)

        const widget = {
          type: 'HTML', // whatever
          name: 'flying', // whatever
          draw (ctx, node, widget_width, y, widget_height) {
            Object.assign(
              this.inputEl.style,
              get_position_style(ctx, widget_width, y, node.size[1])
            ) // assign the required style when we are drawn
          }
        }

        /*
              Create an html element and add it to the document.  
              Look at $el in ui.js for all the options here
              */
        widget.inputEl = $el('img', {
          src: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAAAXNSR0IArs4c6QAAALZJREFUKFOFkLERwjAQBPdbgBkInECGaMLUQDsE0AkRVRAYWqAByxldPPOWHwnw4OBGye1p50UDSoA+W2ABLPN7i+C5dyC6R/uiAUXRQCs0bXoNIu4QPQzAxDKxHoALOrZcqtiyR/T6CXw7+3IGHhkYcy6BOR2izwT8LptG8rbMiCRAUb+CQ6WzQVb0SNOi5Z2/nX35DRyb/ENazhpWKoGwrpD6nICp5c2qogc4of+c7QcrhgF4Aa/aoAFHiL+RAAAAAElFTkSuQmCC'
        })
        // widget.inputEl = $el('button', {
        //   innerText: 'Start'
        // })
        document.body.appendChild(widget.inputEl)
        widget.inputEl.addEventListener('click', () => {
          shareScreenAndUpload(widget.inputEl)
        })
        // console.log('widget.inputEl',widget.inputEl)

        /*
              Add the widget, make sure we clean up nicely, and we do not want to be serialized!
              */
        this.addCustomWidget(widget)
        this.onRemoved = function () {
          widget.inputEl.remove()
        }
        this.serialize_widgets = false
      }
    }
  }
})

// 和python实现一样
function run (mutable_prompt, immutable_prompt) {
  // Split the text into an array of words
  const words1 = mutable_prompt.split('\n')

  // Split the text into an array of words
  const words2 = immutable_prompt.split('\n')

  const prompts = []
  for (let i = 0; i < words1.length; i++) {
    words1[i] = words1[i].trim()
    for (let j = 0; j < words2.length; j++) {
      words2[j] = words2[j].trim()
      if (words2[j] && words1[i]) {
        prompts.push(words2[j].replaceAll('``', words1[i]))
      }
    }
  }

  return prompts
}

// 更新ui，计算prompt的组合结果
const updateUI = node => {
  const mutable_prompt_w = node.widgets.filter(
    w => w.name === 'mutable_prompt'
  )[0]
  mutable_prompt_w.inputEl.title = 'Enter keywords, one per line'
  const immutable_prompt_w = node.widgets.filter(
    w => w.name === 'immutable_prompt'
  )[0]
  immutable_prompt_w.inputEl.title =
    'Enter prompts, one per line, variables represented by ``'

  const max_count = node.widgets.filter(w => w.name === 'max_count')[0]
  let prompts = run(mutable_prompt_w.value, immutable_prompt_w.value)

  prompts = prompts.slice(0, max_count.value)

  max_count.value = prompts.length

  // 如果已经存在,删除
  const pw = node.widgets.filter(w => w.name === 'prompts')[0]
  if (pw) {
    // node.widgets[pos].onRemove?.();
    pw.value = prompts.join('\n\n')
    pw.inputEl.title = `Total of ${prompts.length} prompts`
  } else {
    // 动态添加
    const w = ComfyWidgets.STRING(
      node,
      'prompts',
      ['STRING', { multiline: true }],
      app
    ).widget
    w.inputEl.readOnly = true
    w.inputEl.style.opacity = 0.6
    w.value = prompts.join('\n\n')
    w.inputEl.title = `Total of ${prompts.length} prompts`
  }

  // 移除无关的widget
  //  for (let i = 0; i < node.widgets.length; i++) {
  //   console.log(node.widgets[i]?.name)
  //   if(node.widgets[i]&&!['mutable_prompt','immutable_prompt','max_count','prompts'].includes(node.widgets[i].name)) node.widgets[i].onRemove?.();
  // }

  // console.log(node.widgets.length,node.size);

  node.widgets.length = 5
  node.onResize?.(node.size)
}

const exportGraph = () => {
  const graph = app.graph

  var clipboard_info = {
    nodes: [],
    links: []
  }
  var index = 0
  var selected_nodes_array = []
  for (var i in graph._nodes_in_order) {
    var node = graph._nodes_in_order[i]
    if (node.clonable === false) continue
    node._relative_id = index
    selected_nodes_array.push(node)
    index += 1
  }

  for (var i = 0; i < selected_nodes_array.length; ++i) {
    var node = selected_nodes_array[i]
    var cloned = node.clone()
    if (!cloned) {
      console.warn('node type not found: ' + node.type)
      continue
    }

    let nc = {}
    let n = cloned.serialize()
    for (const key in n) {
      if (
        [
          'type',
          'pos',
          'size',
          'flags',
          'order',
          'mode',
          'inputs',
          'outputs',
          'properties',
          'widgets_values'
        ].includes(key)
      ) {
        nc[key] = n[key]
      }
    }

    clipboard_info.nodes.push(nc)

    if (node.inputs && node.inputs.length) {
      for (var j = 0; j < node.inputs.length; ++j) {
        var input = node.inputs[j]
        if (!input || input.link == null) {
          continue
        }
        var link_info = graph.links[input.link]
        if (!link_info) {
          continue
        }
        var target_node = graph.getNodeById(link_info.origin_id)
        if (!target_node) {
          continue
        }
        clipboard_info.links.push([
          target_node._relative_id,
          link_info.origin_slot, //j,
          node._relative_id,
          link_info.target_slot,
          target_node.id
        ])
      }
    }
  }
  localStorage.setItem('_Mixlab_clipboard', JSON.stringify(clipboard_info))

  return clipboard_info
}

const my = {
  nodes: [
    {
      type: 'LoadImage',
      pos: [719.5130480797907, 172.9437092123179],
      size: { 0: 315, 1: 314 },
      flags: {},
      order: 0,
      mode: 0,
      outputs: [
        { name: 'IMAGE', type: 'IMAGE', links: [], shape: 3 },
        { name: 'MASK', type: 'MASK', links: null, shape: 3 }
      ],
      properties: { 'Node name for S&R': 'LoadImage' },
      widgets_values: ['00204211b3c71288c12ed66516a1a20a.jpg', 'image']
    },
    {
      type: 'ControlNetLoader',
      pos: [1199.5130480797907, -331.0562907876821],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 1,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_canny.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1204.5130480797907, -169.0562907876821],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 2,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1p_sd15_depth.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1206.5130480797907, -20.056290787682087],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 3,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['t2iadapter_seg-fp16.safetensors']
    },
    {
      type: 'ControlNetLoader',
      pos: [1209.5130480797907, 125.94370921231791],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 4,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_openpose.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1214.5130480797907, 293.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 5,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11e_sd15_ip2p.safetensors']
    },
    {
      type: 'ControlNetLoader',
      pos: [1212.5130480797907, 461.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 6,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11p_sd15_inpaint.pth']
    },
    {
      type: 'ControlNetLoader',
      pos: [1216.5130480797907, 636.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 7,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1e_sd15_tile.bin']
    },
    {
      type: 'ControlNetLoader',
      pos: [1227.5130480797907, 804.9437092123179],
      size: { 0: 415.221923828125, 1: 58.84859848022461 },
      flags: {},
      order: 8,
      mode: 0,
      outputs: [
        { name: 'CONTROL_NET', type: 'CONTROL_NET', links: [], shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetLoader' },
      widgets_values: ['control_v11f1e_sd15_tile.bin']
    },
    {
      type: 'ControlNetApplyAdvanced',
      pos: [1816, 94],
      size: { 0: 315, 1: 166 },
      flags: {},
      order: 9,
      mode: 0,
      inputs: [
        { name: 'positive', type: 'CONDITIONING', link: null },
        { name: 'negative', type: 'CONDITIONING', link: null },
        { name: 'control_net', type: 'CONTROL_NET', link: null, slot_index: 2 },
        { name: 'image', type: 'IMAGE', link: null, slot_index: 3 }
      ],
      outputs: [
        { name: 'positive', type: 'CONDITIONING', links: null, shape: 3 },
        { name: 'negative', type: 'CONDITIONING', links: null, shape: 3 }
      ],
      properties: { 'Node name for S&R': 'ControlNetApplyAdvanced' },
      widgets_values: [1, 0, 1]
    }
  ],
  links: [
    [1, 0, 9, 2, 2],
    [0, 0, 9, 3, 1]
  ]
}

// 添加workflow
const importWorkflow = my => {
  localStorage.setItem('litegrapheditor_clipboard', JSON.stringify(my))
  app.canvas.pasteFromClipboard()
}

const node = {
  name: 'RandomPrompt',
  async setup (a) {
    for (const node of app.graph._nodes) {
      if (node.comfyClass === 'RandomPrompt') {
        console.log('#setup', node)
        updateUI(node)
      }
    }
    console.log('[logging]', 'loaded graph node: ', exportGraph(app.graph))
  },
  addCustomNodeDefs (defs, app) {
    console.log(
      '[logging]',
      'add custom node definitions',
      'current nodes:',
      defs
    )
    // 在这里进行 语言切换
    for (const nodeName in defs) {
      if (nodeName === 'RandomPrompt') {
        // defs[nodeName].category
        // defs[nodeName].display_name
      }
    }
  },
  loadedGraphNode (node, app) {
    // Fires for each node when loading/dragging/etc a workflow json or png
    // If you break something in the backend and want to patch workflows in the frontend
    // This is the place to do this
    // console.log("[logging]", "loaded graph node: ", exportGraph(node.graph));
  },
  async nodeCreated (node) {
    if (node.comfyClass === 'RandomPrompt') {
      updateUI(node)
    }

    if (node.comfyClass === 'RunWorkflow') {
      const pw = node.widgets.filter(w => w.name === 'workflow')[0]
      console.log('nodeCreated', pw)
      // if (pw) {
      // 	// node.widgets[pos].onRemove?.();
      //   pw.value = prompts.join('\n\n');
      //   // pw.inputEl=document.createElement('input');
      // }

      //  node.widgets.length = 1;
      node.onResize?.(node.size)
    }
  },
  async beforeRegisterNodeDef (nodeType, nodeData, app) {
    // 注册节点前，可以修改节点的数据
    // 可以获取得到其他节点数据

    // 汉化
    // app.graph._nodes // title ='123'

    if (nodeData.name === 'SaveTransparentImage') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)
        console.log('executed', message)
        const { image_path } = message
        if (image_path) {
        }
        return r
      }
    }

    if (nodeData.name === 'WSServer') {
      // Create the button widget for selecting the files
      // node.addWidget(
      //   'button',
      //   'choose file to upload',
      //   'video',
      //   () => {
      //     console.log('click')
      //   }
      // )
      // uploadWidget.serialize = false
      // const onExecuted = nodeType.prototype.onExecuted
      // nodeType.prototype.onExecuted = function (message) {
      //   const r = onExecuted?.apply?.(this, arguments)
      //   console.log('executed', message)
      //   const upload = this.widgets.filter(w => w.name === 'upload')[0]
      //   console.log('executed', this.widgets)
      //   // navigator.mediaDevices
      //   //   .getDisplayMedia({ video: true })
      //   //   .then(stream => {
      //   //     const videoElement = document.createElement('video')
      //   //     videoElement.srcObject = stream
      //   //     videoElement.autoplay = true
      //   //     const canvasElement = document.createElement('canvas')
      //   //     const context = canvasElement.getContext('2d')
      //   //     videoElement.addEventListener('loadedmetadata', () => {
      //   //       canvasElement.width = videoElement.videoWidth
      //   //       canvasElement.height = videoElement.videoHeight
      //   //       setInterval(async () => {
      //   //         context.drawImage(
      //   //           videoElement,
      //   //           0,
      //   //           0,
      //   //           canvasElement.width,
      //   //           canvasElement.height
      //   //         )
      //   //         const imageData = canvasElement.toDataURL()
      //   //         upload.value = await uploadScreenshot(imageData)
      //   //       }, 200)
      //   //     })
      //   //   })
      //   //   .catch(error => {
      //   //     console.error('Error getting screen share:', error)
      //   //   })
      //   return r
      // }
    }

    if (nodeData.name === 'RandomPrompt') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)

        let prompts = message.prompts
        console.log('executed', message)
        // console.log('#RandomPrompt', this.widgets)
        const pw = this.widgets.filter(w => w.name === 'prompts')[0]

        if (pw) {
          // node.widgets[pos].onRemove?.();
          pw.value = prompts.join('\n\n')
          pw.inputEl.title = `Total of ${prompts.length} prompts`
        } else {
          // 动态添加
          const w = ComfyWidgets.STRING(
            node,
            'prompts',
            ['STRING', { multiline: true }],
            app
          ).widget
          w.inputEl.readOnly = true
          w.inputEl.style.opacity = 0.6
          w.value = prompts.join('\n\n')
          w.inputEl.title = `Total of ${prompts.length} prompts`
        }

        this.widgets.length = 5

        this.onResize?.(this.size)

        return r
      }
    }
  }
}

app.registerExtension(node)

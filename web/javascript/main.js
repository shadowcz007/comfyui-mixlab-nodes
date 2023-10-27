import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'

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
const importWorkflow = (my) => {
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

    if (nodeData.name === 'RunWorkflow') {
      const onExecuted = nodeType.prototype.onExecuted
      nodeType.prototype.onExecuted = function (message) {
        const r = onExecuted?.apply?.(this, arguments)

        return r
      }
    }
  }
}

app.registerExtension(node)

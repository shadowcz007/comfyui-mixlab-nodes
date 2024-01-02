import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'
import { ComfyWidgets } from '../../../scripts/widgets.js'
import { $el } from '../../../scripts/ui.js'
import { closeIcon } from './svg_icons.js'

import {
  GroupNodeConfig,
  GroupNodeHandler
} from '../../../extensions/core/groupNode.js'

function deepEqual (obj1, obj2) {
  if (typeof obj1 !== typeof obj2) {
    return false
  }

  if (typeof obj1 !== 'object' || obj1 === null || obj2 === null) {
    return obj1 === obj2
  }

  const keys1 = Object.keys(obj1)
  const keys2 = Object.keys(obj2)

  if (keys1.length !== keys2.length) {
    return false
  }

  for (let key of keys1) {
    if (!deepEqual(obj1[key], obj2[key])) {
      return false
    }
  }

  return true
}

async function get_nodes_map () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  const res = await fetch(`${url}/mixlab/nodes_map`, {
    method: 'POST',
    body: JSON.stringify({
      data: 'json'
    })
  })
  return await res.json()
}

function get_url () {
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`
  return url
}

async function get_my_app (filename = null, category = '') {
  let url = get_url()
  const res = await fetch(`${url}/mixlab/workflow`, {
    method: 'POST',
    body: JSON.stringify({
      task: 'my_app',
      filename,
      category,
      admin: true
    })
  })
  let result = await res.json()
  let data = []
  try {
    for (const res of result.data) {
      let { app, workflow } = res.data
      if (app.filename)
        data.push({
          ...app,
          data: workflow,
          date: res.date
        })
    }
  } catch (error) {}
  return data
}

function loadCSS (url) {
  var link = document.createElement('link')
  link.rel = 'stylesheet'
  link.type = 'text/css'
  link.href = url
  document.getElementsByTagName('head')[0].appendChild(link)
}

var cssURL =
  'https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown-light.min.css'
loadCSS(cssURL)

function injectCSS (css) {
  // 检查页面中是否已经存在具有相同内容的style标签
  const existingStyle = document.querySelector('style')
  if (existingStyle && existingStyle.textContent === css) {
    return // 如果已经存在相同的样式，则不进行注入
  }

  // 创建一个新的style标签，并将CSS内容注入其中
  const style = document.createElement('style')
  style.textContent = css

  // 将style标签插入到页面的head元素中
  const head = document.querySelector('head')
  head.appendChild(style)
}

injectCSS(`::-webkit-scrollbar {
  width: 2px;
}

@keyframes loading_mixlab {
  0% {
    background-color: green;
  }

  50% {
    background-color: lightgreen;
  }

  100% {
    background-color: green;
  }
}

.loading_mixlab {
  background-color: green;
  animation-name: loading_mixlab;
  animation-duration: 2s;
  animation-iteration-count: infinite;
}`)

async function getCustomnodeMappings (mode = 'url') {
  // mode = "local";
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  let nodes = {}

  const data = (await get_nodes_map()).data

  for (let url in data) {
    let n = data[url]
    for (let node of n[0]) {
      // if(node=='CLIPSeg')console.log('#CLIPSeg',n)
      nodes[node] = { url, title: n[1].title_aux }
    }
  }

  // try {
  //   const response = await fetch(`${url}/customnode/getmappings?mode=${mode}`)
  //   const data = await response.json()
  //   for (let url in data) {
  //     let n = data[url]
  //     for (let node of n[0]) {
  //       // if(node=='CLIPSeg')console.log('#CLIPSeg',n)
  //       nodes[node] = { url, title: n[1].title_aux }
  //     }
  //   }
  // } catch (error) {
  //   const data = (await get_nodes_map()).data

  //   for (let url in data) {
  //     let n = data[url]
  //     for (let node of n[0]) {
  //       // if(node=='CLIPSeg')console.log('#CLIPSeg',n)
  //       nodes[node] = { url, title: n[1].title_aux }
  //     }
  //   }
  // }

  return nodes
}

const missingNodeGithub = (missingNodeTypes, nodesMap) => {
  let ts = {}

  Array.from(new Set(missingNodeTypes), n => {
    if (nodesMap[n]) {
      let title = nodesMap[n].title
      if (!ts[title]) {
        ts[title] = {
          title,
          nodes: {},
          url: nodesMap[n].url
        }
      }
      ts[title].nodes[n] = 1
    } else {
      ts[n] = {
        title: n,
        nodes: {},
        url: `https://github.com/search?q=${n}&type=code`
      }
      ts[n].nodes[n] = 1
    }
  })

  return Array.from(Object.values(ts), n => {
    const url = n.url
    return `<li style="color: white;
   background: black;
   padding: 8px;
   font-size: 12px;">${n.title}<a href="${url}" target="_blank"> 🔗</a></li>`
  })
}

let nodesMap

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

app.showMissingNodesError = async function (
  missingNodeTypes,
  hasAddedNodes = true
) {
  nodesMap =
    nodesMap && Object.keys(nodesMap).length > 0
      ? nodesMap
      : await getCustomnodeMappings('url')

  // console.log('#nodesMap', nodesMap)
  // console.log('###MIXLAB', missingNodeTypes, hasAddedNodes)
  this.ui.dialog.show(
    `When loading the graph, the following node types were not found: <ul>${missingNodeGithub(
      missingNodeTypes,
      nodesMap
    ).join('')}</ul>${
      hasAddedNodes
        ? 'Nodes that have failed to load will show as red on the graph.'
        : ''
    }`
  )
  this.logging.addEntry('Comfy.App', 'warn', {
    MissingNodes: missingNodeTypes
  })
}

// app.registerExtension({
//   name: 'Comfy.MDNote',
//   registerCustomNodes () {
//     class NoteNode {
//       // color = LGraphCanvas.node_colors.yellow.color
//       // bgcolor = LGraphCanvas.node_colors.yellow.bgcolor
//       // groupcolor = LGraphCanvas.node_colors.yellow.groupcolor
//       constructor () {
//         if (!this.properties) {
//           this.properties = {}
//           this.properties.text = ''
//         }
//         console.log('NoteNode1', this)

//         const widget = {
//           type: 'div',
//           name: 'input_color',
//           draw (ctx, node, widget_width, y, widget_height) {
//             Object.assign(
//               this.div.style,
//               get_position_style(
//                 ctx,
//                 widget_width,
//                 44,
//                 node.size[1]
//               )
//             )
//           }
//         }

//         widget.div = $el('div', {});
//         widget.div.innerText='1111'

//         document.body.appendChild(widget.div)

//         this.addCustomWidget(widget)

//         this.serialize_widgets = true
//         this.isVirtualNode = true
//       }
//     }

//     // Load default visibility

//     LiteGraph.registerNodeType(
//       'MDNote',
//       Object.assign(NoteNode, {
//         title_mode: LiteGraph.NORMAL_TITLE,
//         title: 'MDNote',
//         collapsable: true
//       })
//     )

//     NoteNode.category = '♾️Mixlab/utils'
//   },

// })

async function fetchReadmeContent (url) {
  try {
    // var repo = 'owner/repo'; // 仓库的拥有者和名称
    var match = url.match(/github.com\/([^/]+\/[^/]+)/)
    var repo = match[1]
    var url = `https://api.github.com/repos/${repo}/readme`
    var response = await fetch(url)
    var data = await response.json()
    var readmeUrl = data.download_url

    var readmeResponse = await fetch(readmeUrl)
    var content = await readmeResponse.text()
    // console.log(content) // 在控制台输出readme.md文件的内容

    return content
  } catch (error) {
    console.log('获取readme.md文件信息失败:', error)
  }
}

function createModal (url, markdown, title) {
  // Create modal element
  var div =
    document.querySelector('#mix-modal') || document.createElement('div')
  div.id = 'mix-modal'
  div.innerHTML = ''
  div.style.cssText = `width: 100%;
    z-index: 9990;
    height: 100vh;
    display: flex;
    color: var(--descrip-text);
    position: fixed;
    top: 0;
    left: 0;
    `

  var modal = document.createElement('div')

  div.appendChild(modal)
  modal.classList.add('modal-body')
  // Set modal styles
  modal.style.cssText = `
    background: white;
    height: 80vh;
    position: fixed;
    overflow:hidden;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999;
    border-radius: 4px;
    box-shadow: 4px 4px 14px rgba(255,255,255,0.5);

  `
  // Create modal content area
  var modalContent = document.createElement('div')
  modalContent.classList.add('modal-content')
  // Create modal header
  const headerElement = document.createElement('div')
  headerElement.classList.add('modal-header')
  headerElement.style.cssText = `
    display: flex;
    padding: 20px 24px 8px 24px;
    justify-content: space-between;
  `

  const headTitleElement = document.createElement('a')
  headTitleElement.classList.add('header-title')
  headTitleElement.style.cssText = `
    color: var(--descrip-text);
    font-size: 18px;
    display: flex;
    align-items: center;
    flex: 1;
    overflow: hidden;
    text-decoration: none;
    font-weight: bold;
  `
  headTitleElement.onmouseenter = function () {
    headTitleElement.style.color = 'var(--comfy-menu-bg)'
  }
  headTitleElement.onmouseleave = function () {
    headTitleElement.style.color = 'var(--descrip-text)'
  }
  headTitleElement.textContent = title || ''
  headTitleElement.href = url
  headTitleElement.target = '_blank'
  const linkIcon = document.createElement('small')
  linkIcon.textContent = '🔗'
  headTitleElement.appendChild(linkIcon)
  headerElement.appendChild(headTitleElement)

  // Create close button
  const closeButton = document.createElement('span')
  closeButton.classList.add('close')
  closeButton.innerHTML = closeIcon
  // Set close button styles
  closeButton.style.cssText = `
      padding: 4px;
      cursor: pointer;
      width: 32px;
      height: 32px;
      display: flex;
      justify-content: center;
      align-items: center;
      user-select: none;
      fill: var(--descrip-text);
      `
  closeButton.onmouseenter = function () {
    closeButton.style.fill = 'var(--comfy-menu-bg)'
  }
  closeButton.onmouseleave = function () {
    closeButton.style.fill = 'var(--descrip-text)'
  }

  headerElement.appendChild(closeButton)

  // Click event to close the modal
  function closeMixModal () {
    div.style.display = 'none'
    window.removeEventListener('keydown', MixModalEscKeyEvent)
  }
  closeButton.onclick = function () {
    closeMixModal()
  }

  // Set modal content area styles
  modalContent.style.cssText = `
    position: relative;
    padding: 0px;
    overflow: hidden scroll;;
    height: 100%;
    min-width:300px
    `

  // Append close button to modal content area
  modal.appendChild(headerElement)

  // Create element for displaying Markdown content
  var markdownContent = document.createElement('div')
  markdownContent.classList.add('markdown-content', 'markdown-body')
  markdownContent.style.cssText = `max-width: 50vw;padding: 0px 24px 100px 24px;`

  showdown.setFlavor('github')
  var converter = new showdown.Converter()

  var html = converter.makeHtml(markdown)

  // Hide images in the markdown when they fail to load
  var regex = /<img[^>]+src="?([^"\s]+)"?[^>]*>/g
  html = html.replace(regex, function (match, src) {
    return `<img src="${src}" onerror="this.style.display='none'">`
  })

  // Open links in a new tab or window
  html = html.replace(/<a/g, '<a target="_blank"')

  // Fix href attribute to absolute path
  html = html.replace(
    /<a([^>]+href=["'])(?!https?:\/\/)([^"'>]+)/g,
    function (match, prefix, path) {
      var absolutePath = url + '/' + path
      return '<a' + prefix + absolutePath
    }
  )

  markdownContent.innerHTML = html

  // Append Markdown content element to modal content area
  modalContent.appendChild(markdownContent)

  // Append modal content area to modal element
  modal.appendChild(modalContent)

  const footerElement = document.createElement('div')
  footerElement.style.cssText = `
      position: absolute;
      left: 0;
      right: 0;
      text-align: right;
      padding:10px;
      font-size:12px
  `

  const footerText = document.createElement('a')
  footerText.href = 'https://github.com/shadowcz007/comfyui-mixlab-nodes'
  footerText.innerText = 'Support by Mixlab'
  footerText.style.cssText = `color:inherit`
  footerText.target = '_blank'
  footerText.onmouseenter = function () {
    footerText.style.color = 'var(--input-text)'
  }
  footerText.onmouseleave = function () {
    footerText.style.color = 'inherit'
  }

  footerText.onclick = function (e) {
    e.stopPropagation()
  }
  footerElement.appendChild(footerText)

  div.appendChild(footerElement)

  // Append modal element to the page
  if (!document.querySelector('#mix-modal')) {
    document.body.appendChild(div)
  }
  function MixModalEscKeyEvent (event) {
    if (event.key == 'Escape') {
      closeMixModal()
    }
  }
  window.removeEventListener('keydown', MixModalEscKeyEvent)
  window.addEventListener('keydown', MixModalEscKeyEvent)

  const bgElement = document.createElement('div')
  bgElement.classList.add('mix-modal-bg')
  bgElement.style.cssText = `
    width:100%;
    height:100%;
    background-color: rgba(0,0,0,0.8);
  `
  bgElement.onclick = function () {
    closeMixModal()
  }

  div.appendChild(bgElement)
}

app.registerExtension({
  name: 'Comfy.Mixlab.ui',
  init () {
    LGraphCanvas.prototype.helpAboutNode = async function (node) {
      nodesMap =
        nodesMap && Object.keys(nodesMap).length > 0
          ? nodesMap
          : await getCustomnodeMappings('url')

      console.log('node & node map', node, nodesMap, nodesMap[node.type])
      let repo = nodesMap[node.type]
      if (repo) {
        let markdown = await fetchReadmeContent(repo.url)
        createModal(repo.url, markdown, repo.title)
      }
    }

    const getNodeMenuOptions = LGraphCanvas.prototype.getNodeMenuOptions // store the existing method
    LGraphCanvas.prototype.getNodeMenuOptions = function (node) {
      // replace it
      const options = getNodeMenuOptions.apply(this, arguments) // start by calling the stored one
      node.setDirtyCanvas(true, true) // force a redraw of (foreground, background)

      return [
        {
          content: 'Help ♾️Mixlab', // with a name
          callback: () => {
            LGraphCanvas.prototype.helpAboutNode(node)
          } // and the callback
        },
        null,
        ...options
      ] // and return the options
    }

    const getGroupMenuOptions = LGraphCanvas.prototype.getGroupMenuOptions // store the existing method
    LGraphCanvas.prototype.getGroupMenuOptions = function (node) {
      // replace it
      const options = getGroupMenuOptions.apply(this, arguments) // start by calling the stored one
      node.setDirtyCanvas(true, true) // force a redraw of (foreground, background)

      // templete
      const key = 'Comfy.NodeTemplates'
      let templates = localStorage.getItem(key)
      if (templates) {
        templates = JSON.parse(templates)
      } else {
        templates = []
      }
      const store = () => localStorage.setItem(key, JSON.stringify(templates))

      return [
        {
          content: 'Clone Group ♾️Mixlab', // with a name
          callback: async (value, opts, e, menu, group) => {
            const clipboardAction = async cb => {
              // We use the clipboard functions but dont want to overwrite the current user clipboard
              // Restore it after we've run our callback
              const old = localStorage.getItem('litegrapheditor_clipboard')
              await cb()
              localStorage.setItem('litegrapheditor_clipboard', old)
            }

            clipboardAction(async () => {
              let name = group.title
              let nodes = group._nodes

              app.canvas.copyToClipboard(nodes)
              let data = localStorage.getItem('litegrapheditor_clipboard')
              data = JSON.parse(data)

              for (let i = 0; i < nodes.length; i++) {
                const node = app.graph.getNodeById(nodes[i].id)
                const nodeData = node.serialize()

                let groupData = GroupNodeHandler.getGroupData(node)
                if (groupData) {
                  groupData = groupData.nodeData
                  if (!data.groupNodes) {
                    data.groupNodes = {}
                  }
                  data.groupNodes[nodeData.name] = groupData
                  data.nodes[i].type = nodeData.name
                }
              }

              await GroupNodeConfig.registerFromWorkflow(data.groupNodes, {})
              localStorage.setItem(
                'litegrapheditor_clipboard',
                JSON.stringify(data)
              )
              app.canvas.pasteFromClipboard()
            })
          } // and the callback
        },
        {
          content: 'Save Group as Template ♾️Mixlab', // with a name
          callback: async (value, opts, e, menu, group) => {
            // console.log(options)

            const clipboardAction = async cb => {
              // We use the clipboard functions but dont want to overwrite the current user clipboard
              // Restore it after we've run our callback
              const old = localStorage.getItem('litegrapheditor_clipboard')
              await cb()
              localStorage.setItem('litegrapheditor_clipboard', old)
            }

            clipboardAction(() => {
              let name = group.title + ' ♾️Mixlab'
              let nodes = group._nodes

              app.canvas.copyToClipboard(nodes)
              let data = localStorage.getItem('litegrapheditor_clipboard')
              data = JSON.parse(data)

              for (let i = 0; i < nodes.length; i++) {
                const node = app.graph.getNodeById(nodes[i].id)
                const nodeData = node.serialize()

                let groupData = GroupNodeHandler.getGroupData(node)
                if (groupData) {
                  groupData = groupData.nodeData
                  if (!data.groupNodes) {
                    data.groupNodes = {}
                  }
                  data.groupNodes[nodeData.name] = groupData
                  data.nodes[i].type = nodeData.name
                }
              }

              templates.push({
                name,
                data: JSON.stringify(data)
              })
              store()
            })
          } // and the callback
        },
        null,
        ...options
      ] // and return the options
    }
    LGraphCanvas.prototype.centerOnNode = function (node) {
      // console.log(node)
      var dpr = window.devicePixelRatio || 1 // 获取设备像素比
      this.ds.offset[0] =
        -node.pos[0] -
        node.size[0] * 0.5 +
        (this.canvas.width * 0.5) / (this.ds.scale * dpr) // 考虑设备像素比
      this.ds.offset[1] =
        -node.pos[1] -
        node.size[1] * 0.5 +
        (this.canvas.height * 0.5) / (this.ds.scale * dpr) // 考虑设备像素比
      this.setDirty(true, true)
    }
  },
  setup () {
    setTimeout(async () => {
      // Add canvas menu options
      const orig = LGraphCanvas.prototype.getCanvasMenuOptions

      const apps = await get_my_app()

      let apps_map = { '0': [] }

      for (const app of apps) {
        if (app.category) {
          if (!apps_map[app.category]) apps_map[app.category] = []
          apps_map[app.category].push(app)
        } else {
          apps_map['0'].push(app)
        }
      }

      let apps_opts = []
      for (const category in apps_map) {
        console.log('category',typeof(category))
        if (category === '0') {
          apps_opts.push(
            ...Array.from(apps_map[category], a => {
              return {
                content: a.name,
                has_submenu: false,
                callback: async () => {
                  try {
                    let item = (await get_my_app(a.filename))[0]
                    if (item) {
                      // console.log(item.data)
                      app.loadGraphData(item.data)
                      setTimeout(() => {
                        const node = app.graph._nodes_in_order[0]
                        if (!node) return
                        app.canvas.centerOnNode(node)
                        app.canvas.setZoom(0.5)
                      }, 1000)
                    }
                  } catch (error) {}
                }
              }
            })
          )
        } else {
          // 二级
          apps_opts.push({
            content:  '🚀 '+category,
            has_submenu: true,
            disabled: false,
            submenu: {
              options: Array.from(apps_map[category], a => {
                return {
                  content: a.name,
                  callback: async () => {
                    try {
                      let item = (await get_my_app(a.filename, a.category))[0]
                      if (item) {
                        // console.log(item.data)
                        app.loadGraphData(item.data)
                        setTimeout(() => {
                          const node = app.graph._nodes_in_order[0]
                          if (!node) return
                          app.canvas.centerOnNode(node)
                          app.canvas.setZoom(0.5)
                        }, 1000)
                      }
                    } catch (error) {}
                  }
                }
              })
            }
          })
        }
      }

      // console.log('apps',apps_map, apps_opts,apps)
      LGraphCanvas.prototype.getCanvasMenuOptions = function () {
        const options = orig.apply(this, arguments)

        options.push(
          null,
          {
            content: `Nodes Map ♾️Mixlab`,
            disabled: false,
            callback: async () => {
              nodesMap =
                nodesMap && Object.keys(nodesMap).length > 0
                  ? nodesMap
                  : await getCustomnodeMappings('url')

              const nodesDiv = document.createDocumentFragment()
              const nodes = (await app.graphToPrompt()).output

              // console.log('[Mixlab]', 'loaded graph node: ', app)
              let div =
                document.querySelector('#mixlab_find_the_node') ||
                document.createElement('div')
              div.id = 'mixlab_find_the_node'
              div.style = `
               flex-direction: column;
               align-items: end;
               display:flex;position: absolute; 
               top: 50px; left: 50px; width: 200px; 
               color: var(--descrip-text);
               background-color: var(--comfy-menu-bg);
               padding: 10px; 
               border: 1px solid black;z-index: 999999999;padding-top: 0;`

              div.innerHTML = ''

              let btn = document.createElement('div')
              btn.style = `display: flex;
             width: calc(100% - 24px);
             justify-content: space-between;
             align-items: center;
             padding: 0 12px;
             height: 44px;`
              let btnB = document.createElement('button')
              let textB = document.createElement('p')
              btn.appendChild(textB)
              btn.appendChild(btnB)
              textB.style.fontSize = '12px'
              textB.innerText = `Locate and navigate nodes ♾️Mixlab`

              btnB.style = `float: right; border: none; color: var(--input-text);
             background-color: var(--comfy-input-bg); border-color: var(--border-color);cursor: pointer;`
              btnB.addEventListener('click', () => {
                div.style.display = 'none'
              })
              btnB.innerText = 'X'

              // 悬浮框拖动事件
              div.addEventListener('mousedown', function (e) {
                var startX = e.clientX
                var startY = e.clientY
                var offsetX = div.offsetLeft
                var offsetY = div.offsetTop

                function moveBox (e) {
                  var newX = e.clientX
                  var newY = e.clientY
                  var deltaX = newX - startX
                  var deltaY = newY - startY
                  div.style.left = offsetX + deltaX + 'px'
                  div.style.top = offsetY + deltaY + 'px'
                }

                function stopMoving () {
                  document.removeEventListener('mousemove', moveBox)
                  document.removeEventListener('mouseup', stopMoving)
                }

                document.addEventListener('mousemove', moveBox)
                document.addEventListener('mouseup', stopMoving)
              })

              div.appendChild(btn)

              const updateNodes = (ns, nd) => {
                let appInfoNodes = {}
                try {
                  let appInfo = app.graph._nodes.filter(
                    n => n.type === 'AppInfo'
                  )[0]
                  if (appInfo) {
                    appInfoNodes[appInfo.id] = 2
                    for (const id of appInfo.widgets[1].value.split('\n')) {
                      if (id && id.trim() && parseInt(id)) {
                        appInfoNodes[id] = 0
                      }
                    }
                    for (const id of app.graph._nodes
                      .filter(n => n.type === 'AppInfo')[0]
                      .widgets[2].value.split('\n')) {
                      if (id && id.trim() && parseInt(id)) {
                        appInfoNodes[id] = 1
                      }
                    }
                  }
                } catch (error) {
                  console.log(error)
                }

                for (let nodeId in ns) {
                  let n = ns[nodeId].title || ns[nodeId].class_type
                  if (nodesMap[n]) {
                    const { url, title } = nodesMap[n]
                    let d = document.createElement('button')
                    d.style = `text-align: left;
                    margin:6px;
                    color: var(--input-text);
                   background-color: var(--comfy-input-bg); 
                   border-color: ${
                     appInfoNodes[nodeId] >= 0
                       ? appInfoNodes[nodeId] === 1
                         ? 'blue'
                         : 'red'
                       : 'var(--border-color)'
                   };
                   cursor: pointer;`

                    if (appInfoNodes[nodeId] === 2) {
                      // appinfo
                      d.style.backgroundColor = '#326328'
                      d.style.color = '#ffffff'
                      d.style.borderColor = 'transparent'
                    }

                    d.addEventListener('click', () => {
                      // console.log('node')
                      const node = app.graph.getNodeById(nodeId)

                      if (!node) return
                      app.canvas.centerOnNode(node)
                      app.canvas.setZoom(1)
                    })
                    d.addEventListener('mouseover', async () => {
                      // console.log('mouseover')
                      let n = (await app.graphToPrompt()).output
                      if (!deepEqual(n, ns)) {
                        nd.innerHTML = ''
                        updateNodes(n, nd)
                      }
                    })

                    d.innerHTML = `
                   <span>${'#' + nodeId} ${n}</span>
                   <a href="${url}" target="_blank" style="text-decoration: none;">🔗</a>
                   `
                    d.title = title

                    nd.appendChild(d)
                  }
                }
              }

              let nodesDivv = document.createElement('div')
              let appInfoNodes = {}
              try {
                let appInfo = app.graph._nodes.filter(
                  n => n.type === 'AppInfo'
                )[0]
                if (appInfo) {
                  appInfoNodes[appInfo.id] = 2
                  for (const id of appInfo.widgets[1].value.split('\n')) {
                    if (id && id.trim() && parseInt(id)) {
                      appInfoNodes[id] = 0
                    }
                  }
                  for (const id of app.graph._nodes
                    .filter(n => n.type === 'AppInfo')[0]
                    .widgets[2].value.split('\n')) {
                    if (id && id.trim() && parseInt(id)) {
                      appInfoNodes[id] = 1
                    }
                  }
                }
              } catch (error) {
                console.log(error)
              }

              for (let nodeId in nodes) {
                let n = nodes[nodeId].class_type
                if (nodesMap[n]) {
                  const { url, title: _title } = nodesMap[n]
                  let title = app.graph.getNodeById(nodeId).title || _title
                  let d = document.createElement('button')
                  d.style = `text-align: left;
                  margin:6px;
                  color: var(--input-text);
                 background-color: var(--comfy-input-bg); 
                 border-color: ${
                   appInfoNodes[nodeId] >= 0
                     ? appInfoNodes[nodeId] === 1
                       ? 'blue'
                       : 'red'
                     : 'var(--border-color)'
                 };
                 cursor: pointer;`

                  if (appInfoNodes[nodeId] === 2) {
                    // appinfo
                    d.style.backgroundColor = '#326328'
                    d.style.color = '#ffffff'
                    d.style.borderColor = 'transparent'
                  }

                  d.addEventListener('click', () => {
                    console.log('click')
                    const node = app.graph.getNodeById(nodeId)
                    if (!node) return
                    app.canvas.centerOnNode(node)
                    app.canvas.setZoom(1)
                  })
                  d.addEventListener('mouseover', async () => {
                    // console.log('mouseover')
                    let n = (await app.graphToPrompt()).output
                    if (!deepEqual(n, nodes)) {
                      nodesDivv.innerHTML = ''
                      updateNodes(n, nodesDivv)
                    }
                  })

                  d.innerHTML = `
                 <span>${'#' + nodeId} ${title}</span>
                 <a href="${url}" target="_blank" style="text-decoration: none;">🔗</a>
                 `
                  d.title = n

                  nodesDiv.appendChild(d)
                }
              }

              nodesDivv.appendChild(nodesDiv)
              nodesDivv.style = `overflow: scroll;
             height: 70vh;width: 100%;`

              div.appendChild(nodesDivv)

              if (!document.querySelector('#mixlab_find_the_node'))
                document.body.appendChild(div)
            }
          },
          {
            content: 'Workflow App ♾️Mixlab',
            has_submenu: true,
            disabled: false,
            submenu: {
              options:apps_opts
            }
          }
        )

        return options
      }
    }, 1000)
  }
})

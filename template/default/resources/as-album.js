// bare-bones album component, designed to style properly with the rest of my template
// which is why it doesn't use a shadow dom
//
// usage:
//  <as-album>
//     <a href="fullsize1.jpg"><img src=thumb1.jpg alt="image description"/></a>
//     <a href="fullsize2.jpg"><img src=thumb2.jpg alt="image description"/></a>
//     <a href="fullsize3.jpg"><img src=thumb3.jpg alt="image description"/></a>
// </as-album>
//
// This component fires "picturechanged" events when a new image is selected
//
//



const ALBUMTEMPLATE = `
<figure class="albumdisplay">
  <img class="albumdisplayimage" src="" alt=""/>
  <figcaption class="albumdisplaycaption"></figcaption>
</figure>
<div class="albumdisplaythumbscontainer">
</div>
`

const ALBUMSTYLES = `

figure.albumdisplay {
    width: 100%;
    max-width: 100%;
    margin: 0px;
}

figure img.albumdisplayimage {
    object-fit: contain;
    max-width: 100%;
}

.albumdisplaythumbscontainer {
  float: none;
  clear: both;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(100px, 1fr);
  gap: 0.5rem;
  max-height: 140px; 
  height: 140px;
  max-width: 100%;
  overflow: auto; 
  min-height: 0; 
  min-width: 0;

}

.albumdisplaythumbscontainer img {
  width: 100%;
  height: 110px;
  object-fit: contain;
  box-sizing: border-box; 
}

.albumdisplaythumbscontainer img.selected {
  border: red solid 5px;
  background-color: pink;
}
`

class AsAlbum extends HTMLElement {
    constructor() {
        super();
        this._selectedPictureIndex = 0
    }

    connectedCallback() {

        setTimeout((() => {
            this.getListOfPictures()
            this.replaceContents()
            this.populateThumbs()
            this.setSelectThumbnailIndex(0)
        }).bind(this), 0)
    }

    attributeChangedCallback(name, oldValue, newValue) {
    }

    replaceContents() {
        this.replaceChildren()
        this.classList.add("customelement")

        let styleElement = document.createElement("style")
        styleElement.innerHTML = ALBUMSTYLES
        this.innerHTML = ALBUMTEMPLATE
        document.body.appendChild(styleElement)
    }

    getListOfPictures() {
        this._pictures = []
        // grab the list of child elements and construct the list of images
        let links = this.getElementsByTagName("a")
        for (const link of links) {
            const fullsize_url = link.getAttribute("href")
            const img = link.children[0]
            const caption = img.getAttribute("alt")
            const thumb_url = img.getAttribute("src")

            let picture = { "index": this._pictures.length, "fullsize_url": fullsize_url, "caption": caption, "thumb_url": thumb_url }
            this._pictures.push(picture)
        }
    }

    populateThumbs() {
        let container = this.querySelector(".albumdisplaythumbscontainer")
        for (const i of this._pictures) {
            let image_element = document.createElement("img")
            image_element.src = i.thumb_url
            image_element.addEventListener("click", (() => {
                this.setSelectThumbnailIndex(i.index);
            }).bind(this))
            container.appendChild(image_element)
        }
    }

    setSelectThumbnailIndex(index) {
        let thumbContainer = this.querySelector(".albumdisplaythumbscontainer")

        let thumbElements = thumbContainer.querySelectorAll("img")
        for (let i = 0; i < thumbElements.length; ++i) {
            let e = thumbElements[i]
            if (i == index) {
                if (e.classList.contains("selected")) {
                    continue;   // already selected
                }
                this._selectedPictureIndex = index
                e.classList.add("selected")
                e.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" })
                let mainImageElement = this.querySelector(".albumdisplayimage")
                let captionElement = this.querySelector(".albumdisplaycaption")

                let thumbUrl = this._pictures[index].thumb_url
                mainImageElement.src = thumbUrl
                mainImageElement.setAttribute("alt", this._pictures[index].caption)
                captionElement.innerHTML = this._pictures[index].caption

                let event = new CustomEvent("picturechanged", { detail: this._pictures[index] })
                this.dispatchEvent(event)

                let fullsizedImage = new Image()
                fullsizedImage.src = this._pictures[index].fullsize_url
                fullsizedImage.setAttribute("alt", this._pictures[index].caption)
                fullsizedImage.classList.add(...mainImageElement.classList)
                fullsizedImage.decode().then((() => {
                    if (this._selectedPictureIndex == index) {
                        mainImageElement.replaceWith(fullsizedImage)
                    }
                }).bind(this)).catch((decodeError) => {
                    console.log("Something went wrong decoding the full sized image: ", decodeError)
                })
            } else {
                e.classList.remove('selected')
            }
        }
    }
}

customElements.define("as-album", AsAlbum);
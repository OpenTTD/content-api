from ..helpers.enums import License


def validate_is_valid_package(session, data):
    if data:
        session["content_type"] = data["content_type"]
        session["unique_id"] = data["unique_id"]
        session["md5sum"] = data["md5sum"]
        session["md5sum_partial"] = data["md5sum"][0:8]
        # upload-date and filesize are never set before "publish"
    elif "content_type" in session:
        del session["content_type"]
        del session["unique_id"]
        del session["md5sum"]
        del session["md5sum_partial"]


def validate_license(session):
    if "license" not in session:
        session["errors"].append("License is not yet set for this package.")
    elif session["license"] == License.CUSTOM:
        for file_info in session["files"]:
            if file_info["filename"] == "license.txt":
                break
        else:
            session["errors"].append("License is set to custom, but no license.txt is uploaded.")
    else:
        for file_info in session["files"]:
            if file_info["filename"] == "license.txt":
                session["errors"].append(
                    f"License is set to {session['license'].value}; this does not require uploading 'license.txt'."
                )


def validate_version(session):
    if "version" not in session:
        session["errors"].append("Version is not yet set for this package.")


def validate_has_access(session, package):
    for author in package["authors"]:
        if author.get(session["user"].method) == session["user"].id:
            break
    else:
        session["errors"].append("You do not have permission to upload a new version for this package.")


def validate_unique_version(session, package):
    if "version" not in session:
        return

    for version in package["versions"]:
        if session["version"] == version["version"]:
            session["errors"].append("There is already an entry with the same version for this package.")
            break


def validate_unique_md5sum_partial(session, package):
    if "md5sum_partial" not in session:
        return

    for version in package["versions"]:
        if session["md5sum_partial"] == version["md5sum_partial"]:
            session["errors"].append(
                "There is already an entry with the same md5sum-partial for this package;"
                " this most likely means you are uploading the exact same content."
            )
            break


def validate_new_package(session):
    if "name" not in session:
        session["errors"].append("Name is not yet set for this package.")
    if "description" not in session:
        session["warnings"].append(
            "Description is not yet set for this package; although not mandatory, highly advisable."
        )
    if "url" not in session:
        session["warnings"].append("URL is not yet set for this package; although not mandatory, highly advisable.")
    if "tags" not in session or not session["tags"]:
        session["warnings"].append("Tags is not yet set for this package; although not mandatory, highly advisable.")


def validate_packet_size(session, package):
    # Calculate if this entry wouldn't exceed the OpenTTD packet size if
    # we would transmit this over the wire.

    size = 1 + 4 + 4 + 4  # content-type, content-id, filesize, upload-date
    size += len(session.get("name", package.get("name", ""))) + 2
    size += len(session.get("version", "")) + 2
    size += len(session.get("url", package.get("url", ""))) + 2
    size += len(session.get("description", package.get("description", ""))) + 2
    size += 4  # unique-id
    size += 16  # md5sum
    size += len(session.get("dependencies", [])) * 4
    size += 1
    for tag in session.get("tags", package.get("tags", [])):
        size += len(tag) + 2

    if size > 1400:
        session["errors"].append("Entry would exceed OpenTTD packet size; trim down on your tags.")
